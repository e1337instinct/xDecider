# REPORT.md

## Part 1: What & Why

xDecider is a web app that helps the user decide what show, game, or movie they 
want to engage with based on criteria such as mood, company, and time available. 
The app is for people who struggle with indecision when faced with large, 
unorganized collections to choose from. To avoid the paradox of choice, xDecider 
makes well informed recommendations based on a quick evaluation. The user inputs 
their media library which gets embedded in a local FAISS vector store. The matches 
are processed by GPT-4o-mini which makes the final decision with an explanation.

Working with GPT-4o-mini is difficult because you feel its limits — it interprets 
vague genre descriptions in unexpected ways. I added my own sample library with 
custom descriptions, which became a problem since Among Us (labeled "social") was 
included in nearly every category regardless of mood. I could have simply removed 
it, but I didn't want to dodge the challenge. With around 25 titles in the sample, 
I was disappointed to see some options never get pulled because Among Us kept 
dominating the choices.

---

## Part 2: Iterations

### V1
**Change:** Built the base app using a RAG pipeline with FAISS vector retrieval, 
Python Flask backend, and HTML frontend. A small 16-item sample library was 
created to test recommendations.

**Motivating example:** Test 7 ("I'm feeling sad and need something uplifting") 
returned Among Us, Minecraft, and Inception — none of which are uplifting. Among 
Us appeared in nearly every test regardless of mood.

**Delta:** V1 average score: 3.6/5

**Conclusion:** The library was too small for accurate scoring and the mood 
buttons alone were too vague to capture user intent precisely.

---

### V2
**Change:** Expanded the library from 16 to 27 items for more genre variety. 
Added a free text box for users to describe their mood in their own words. Added 
6 new mood buttons: Uplifting, Competitive, Horror, Dark Humor, Romantic, and 
Nostalgic. Added AI auto-detection of genre when a user adds a new title.

**Motivating example:** Several eval prompts had no matching mood button — 
romantic and horror moods were missing entirely. The biggest driver was not being 
able to properly express mood through buttons alone, which led to adding the 
free text box.

**Delta:** V2 average score: 3.7/5 (+0.1 improvement)

**Conclusion:** Expanding the library reduced repetition and the new mood options 
gave users more precise control. The improvement was modest because Among Us 
continued dominating results despite the larger library. Next step: improve the 
RAG prompt to better infer mood from genre (e.g. MOBA/FPS = competitive).

---

### V3
**Change:** Improved the AI prompt to infer mood compatibility from genres 
automatically. Added confidence percentages to top matches. Allowed multiple mood 
button selections with click-to-deselect. Repositioned the Change Library button 
to prevent accidental clicks. Configured shows to be prioritized for lower time 
availability.

**Motivating example:** Among Us was selected for test 8 ("friends over, r rated 
night") despite being a family-friendly game. I also accidentally clicked Change 
Library 2-3 times during testing and had to reopen the app each time.

**Delta:** V3 average score: 3.9/5 (+0.2 improvement)

**Conclusion:** Improving the prompt's genre-mood awareness had the biggest 
impact. Tests that previously scored 2/5 improved to 3-4/5. Among Us still 
appeared too frequently in retrieval, suggesting the real fix would be improving 
embedding quality or expanding the library further to dilute its influence.

---

## Part 3: Code Walkthrough

When the user clicks "Find My Match", the following chain executes:

**1. templates/index.html** — The browser collects the user's button selections 
and free text, packages them into a JSON object with keys: `time`, `energy`, 
`mood`, `social`, and `free_text`, then sends a POST request to `/api/recommend`.

**2. app.py line 61** (`/api/recommend`) — Flask receives the request, looks up 
the user's session ID, and retrieves their LibraryRAG object from the in-memory 
`rag_store` dictionary. It calls `rag.get_recommendation(mood_data)` and returns 
the result as JSON.

**3. rag.py line 113** (`_mood_to_query()`) — The mood dictionary is converted 
into a natural language query string using `_MOOD_MAP` and `_TIME_MAP`. For 
example, "competitive" becomes "competitive and in the zone, ready to win or 
challenge myself." This string is what gets embedded and searched.

**4. rag.py line 130** (`_search()`) — The query string is embedded using 
OpenAI's text-embedding-3-small model and compared against the FAISS index using 
inner product similarity. The top 5 closest matches are returned with scores.

**5. rag.py line 150** (`get_recommendation()`) — The top matches are formatted 
into a prompt and sent to GPT-4o-mini, which picks the single best option and 
writes a personalized explanation.

One design choice I made was storing each user's library in a dictionary called 
`rag_store` using their session ID as the key. This means the app builds the 
FAISS index once when the user submits their library, rather than rebuilding it 
on every request. I added a pre-loaded sample library for testing purposes since 
the app stores everything in memory and resets on each server restart. An 
alternative I considered was loading the library from a CSV file rather than 
manual input, which would have made testing faster but added file management 
complexity.

---

## Part 4: AI Disclosure & Safety

I used Claude (claude.ai) and Claude Code instead of Kiro due to familiarity and 
time constraints. Claude Code built the initial app scaffold across all files 
(app.py, rag.py, templates/index.html). I used the browser Claude to plan 
architecture, debug errors, and guide me through the development process.

**Specific moments Claude failed:**

1. When installing Claude Code, the initial npm command returned a 404 error due 
to a wrong package name. I recovered by reading the error and trying the 
corrected package name.

2. Claude Code never created a .gitignore file, so my .env file containing my 
real OpenAI API key was committed and pushed to GitHub. GitHub's secret scanning 
blocked the push. I recovered by rewriting the git history, adding .gitignore, 
and revoking and regenerating my API key.

**Safety risks:**

The primary safety risk for xDecider is inappropriate content recommendations. 
For example, when I prompted the app to find something to enjoy with my kids, it 
recommended Elden Ring — a game rated M for violence and suggestive themes. A 
secondary risk is biased output, where Among Us was favored far above any other 
choice regardless of context. A parental filter toggle was not implemented due to 
time constraints but would be a priority in future versions.