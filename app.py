from flask import Flask, request, jsonify, render_template, send_from_directory, make_response
import requests
from bs4 import BeautifulSoup
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from textblob import TextBlob
from io import BytesIO

app = Flask(__name__)

# Route for serving the main HTML page
@app.route('/')
def index():
    return render_template('main.html')

# Route for serving the scraper page
@app.route('/scraper.html')
def scraper():
    return render_template('scraper.html')

# Endpoint to load the content of a URL
@app.route('/load-url', methods=['POST'])
def load_url():
    data = request.json
    url = data.get('url')
    response = requests.get(url)
    return response.text

# Endpoint to scrape data based on tags
@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    tags = data.get('tags', [])
    content = data.get('content', '')

    soup = BeautifulSoup(content, 'html.parser')
    results = {}

    for tag in tags:
        elements = soup.find_all(tag)
        results[tag] = [element.get_text(strip=True) for element in elements]

    return jsonify(results)

# Endpoint to generate CSV file
@app.route('/download-csv', methods=['POST'])
def download_csv():
    data = request.json
    df = pd.DataFrame.from_dict(data, orient='index').transpose()
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    response = make_response(output.read())
    response.headers["Content-Disposition"] = "attachment; filename=scraped_data.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# Endpoint to generate PDF file
@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    data = request.json
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    style = styles["Normal"]

    for tag, texts in data.items():
        story.append(Paragraph(f"Tag: {tag}", styles['Heading2']))
        story.append(Spacer(1, 12))

        for text in texts:
            paragraphs = text.split('\n')
            for paragraph in paragraphs:
                story.append(Paragraph(paragraph, style))
                story.append(Spacer(1, 12))
        
        story.append(Spacer(1, 24))  # Space between different tags

    doc.build(story)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers["Content-Disposition"] = "attachment; filename=scraped_data.pdf"
    response.headers["Content-type"] = "application/pdf"
    return response

# Endpoint to provide visualization data
@app.route('/visualize', methods=['POST'])
def visualize():
    data = request.json
    scraped_data = data.get('scraped_data', {})
    
    # Prepare data for pie chart
    labels = list(scraped_data.keys())
    values = [len(items) for items in scraped_data.values()]
    
    chart_data = {
        'labels': labels,
        'datasets': [{
            'label': 'Number of Items',
            'data': values,
            'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'],
            'hoverOffset': 4
        }]
    }
    
    return jsonify(chart_data)

# Serve static files like CSS
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)
@app.route('/analyze-sentiment', methods=['POST'])
def analyze_sentiment():
    data = request.json
    sentiment_results = {}
    conclusions = []
    
    for tag, texts in data.items():
        sentiments = []
        for text in texts:
            analysis = TextBlob(text)
            sentiments.append(analysis.sentiment.polarity)
        
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        if avg_sentiment > 0:
            sentiment_label = 'positive'
        elif avg_sentiment < 0:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        sentiment_results[tag] = {
            'score': avg_sentiment,
            'label': sentiment_label
        }
    
    # Generate textual conclusions
    positive_count = sum(1 for result in sentiment_results.values() if result['label'] == 'positive')
    negative_count = sum(1 for result in sentiment_results.values() if result['label'] == 'negative')
    neutral_count = sum(1 for result in sentiment_results.values() if result['label'] == 'neutral')
    
    total_tags = len(sentiment_results)
    
    if positive_count > total_tags / 2:
        conclusion = "Overall sentiment is positive."
    elif negative_count > total_tags / 2:
        conclusion = "Overall sentiment is negative."
    else:
        conclusion = "Sentiment is mixed or neutral."
    
    return jsonify({
        'sentiments': sentiment_results,
        'conclusion': conclusion
    })


if __name__ == '__main__':
    app.run(debug=True)
