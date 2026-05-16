# xDecider

An AI-powered web app that recommends the right movie, show, or game from your personal library based on your current mood, energy level, available time, and whether you are solo or with others. Uses a RAG pipeline with a local FAISS vector store and GPT-4o-mini.

## Setup

1. Clone the repository:
   git clone https://github.com/e1337instinct/xDecider.git
   cd xDecider

2. Install dependencies:
   pip install -r requirements.txt

3. Create your .env file:
   cp .env.example .env

4. Add your OpenAI API key to .env:
   OPENAI_API_KEY=your_key_here

## Run

python app.py

Open your browser and go to: http://127.0.0.1:5000

## Usage

1. Add movies, shows, and games to your library (a sample library is pre-loaded)
2. Click Continue and select your mood, energy, and available time, customizable text box is available as well
3. Click Find My Match to get your personalized recommendation

## Eval

To run the evaluation script:

 python eval/eval.py