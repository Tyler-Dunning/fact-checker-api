from flask import Flask, request
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import json
import google.generativeai as genai
from flask_cors import CORS, cross_origin


genai.configure(api_key="AIzaSyDLwll-ubTv5iGGGiskXgC8r5AHb-9dm1Q")


def get_video_id(youtube_url):
    parsed_url = urlparse(youtube_url)
    video_id = parse_qs(parsed_url.query).get('v')
    
    return video_id[0] if video_id else None

def fetch_youtube_transcript(video_url):
    video_id = get_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL."
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        transcript_text = ' '.join([item['text'] for item in transcript])
        return transcript_text
    
    except Exception as e:
        return f"Error retrieving transcript: {e}"

def get_article_content(url):
    if "youtube.com" in url or "youtu.be" in url:
        return fetch_youtube_transcript(url)
    else:
        response = requests.get(url)

        if response.status_code != 200:
            return f"Failed to retrieve the article. Status code: {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')

        article = ""
        article_tags = soup.find_all('article')
        if article_tags:
            article = ' '.join([tag.get_text() for tag in article_tags])
        
        if not article:
            paragraphs = soup.find_all('p')
            article = ' '.join([p.get_text() for p in paragraphs])
        
        return article.strip().replace("\n", "").replace("\t", "")

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

EXCLUDE_POS = ["PRON", "AUX", "DET", "PUNCT", "CCONJ", "ADP"] 
EXCLUDE_LEMMAS = ["be", "do", "have", "will", "can", "may"]

def extract_claims_and_keywords(text, topic):
    doc = nlp(text)
    claims_with_keywords = []

    for sent in doc.sents:
        if topic.lower() in sent.text.lower():
            keywords = []
            for token in sent:
                if (
                    token.pos_ not in EXCLUDE_POS
                    and token.lemma_ not in EXCLUDE_LEMMAS
                    and token.text.lower() not in STOP_WORDS
                    and token.is_alpha
                ):
                    keywords.append(token.text)

            claims_with_keywords.append({
                "claim": sent.text,
                "keywords": keywords[:7]
            })

    return claims_with_keywords

def get_sources_from_claims(claims):
    all_sources = []
    for claim in claims:
        claim_str = ""
        for c in claim:
            claim_str += c + " | "
        params = {'api_token': 'FCEu5WLY3026lFlUi7AkWBW9US3cFRByRAxpbqUz',
                'search': claim_str}
        result_json = requests.get('https://api.thenewsapi.com/v1/news/all?language=en&limit=3&', params=params).json()

        sources = []
        for z in result_json['data']:
            sources.append(z['url'])
        all_sources.append(sources)

    return all_sources

def check_claims_by_source(claims, sources):
    model = genai.GenerativeModel("gemini-1.5-flash")
    results = []
    for i in range(len(claims)):
        claim = claims[i]
        source = sources[i][0]
        results.append(model.generate_content(f"Tell me if the claim {claim} is supported by the following article, reply with ONLY 'True', 'False', 'Misleading', or 'Unsure': {get_article_content(source)}").text[0:-2])
    return results


app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route('/check')
@cross_origin()
def home():
    print("request received")
    url = request.args.get('url')
    phrase = request.args.get('phrase')
    article = ""
    try:
        article = get_article_content(url)
    except:
        return json.dumps({"success": "false"})
    print("article read")
    claims_keywords = extract_claims_and_keywords(article, phrase)
    claims = []
    kws = []
    for ck in claims_keywords:
        claims.append(ck["claim"])
        kws.append(ck["keywords"])

    print("claims found")
    sources = get_sources_from_claims(kws)
    print("sources found")
    verifications = check_claims_by_source(claims, sources)
    print("verified")
    print(verifications)
    result = []
    result.append({"success": "true"})
    for claim, source, verification in zip(claims, sources, verifications):
        result.append({
            "claim": claim,
            "sources": source,
            "rating": verification
        })
    json_res = json.dumps(result, indent=4)
    print("results generated")
    return json_res


if __name__ == '__main__':
    app.run()