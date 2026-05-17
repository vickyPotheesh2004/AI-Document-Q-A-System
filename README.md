# 🔬 ResearchHelp-AI Analysis System: Advanced AI Document Research & Publishing System

ResearchHelp-AI Analysis System is a next-generation, multi-modal document analysis platform that transforms raw files into structured, queryable knowledge bases. By leveraging **semantic embeddings**, **hybrid retrieval (Vector + BM25)**, **LLM streaming**, and **rich multimedia integrations**, it enables deep research Q&A, auto-generated suggestions, and professional academic publishing — all directly from your uploaded files.

---

## ✨ Key Differentiators & Upgrades

- **[NEW] Dynamic 44-Domain Adaptation**: The system automatically detects research domains (e.g., Quantum Computing, Software Engineering, Bioinformatics) in your queries and documents, instantly injecting expert-level analytical frameworks, formatting rules (like LaTeX or architectural paradigms), and specialized lenses into its responses.
- **🎓 IEEE Official Paper Generator**: Synthesize academic manuscripts complete with Abstracts, Literature Reviews, and Methodologies, auto-formatted into professional Times New Roman, two-column style `.docx` files.
- **🧪 Simple English Deep Analysis**: Specialized research mode that breaks down complex domains into simple, jargon-free English using real-world analogies.
- **⚡ Token-by-Token Streaming**: Answers stream in real-time. No more waiting for a full response.
- **🔊 Voice Interface (STT & TTS)**: Ask queries seamlessly using your microphone, and listen to document overviews, AI suggestions, and chat responses via embedded TTS buttons.
- **🖼️ AI Image Generation**: Ask for a "visual understanding" and the system will dynamically paint an AI-generated image (via Pollinations.ai) to explain the concept.
- **📊 Interactive Flowcharts**: Diagrams are rendered live as colored, interactive Mermaid flowcharts matching the app's theme.
- **🧠 Deterministic Confidence Scoring**: Evaluates the retrieved context vs response accuracy deterministically, saving LLM tokens.
- **📄 Comprehensive Export**: Download your entire session in **Markdown**, **HTML**, or fully-styled **Word (.docx)**.

---

## 🚀 Core Features & Capabilities

### 1. Multi-Format Document Ingestion
- Supports **PDF**, **DOCX**, **TXT**, **CSV**, **XLSX**, **PNG**, **JPG** formats.
- **OCR-Powered Extraction**: Uses Tesseract OCR to extract text from scanned documents and images.
- **Structured Data Parsing**: Reads tabular data from CSV/Excel via Pandas.
- Intelligent chunking mechanism to handle massive documents seamlessly.

### 2. Advanced Intent Classification System
At the heart of ResearchHelp-AI-anaylsis-system is a smart routing engine that categorizes every query before processing. This ensures the correct prompt template and analysis logic is applied.

| Intent Category | Trigger Example | Functionality |
|-----------------|-----------------|---------------|
| 📄 `document_qa` | "What hardware is used?" | Direct factual Q&A from the document context. |
| 💡 `suggestion_request` | "How can we improve this?" | Gap analysis and actionable improvement suggestions. |
| 🔬 `research_addon` | "Can we add solar power?" | Technical feasibility assessment and risk analysis. |
| 🧪 `research_analysis` | "Explain Quantum Computing" | Deep analysis in **VERY SIMPLE English** with analogies. |
| 🎓 `ieee_paper_gen` | "Generate an IEEE paper" | Synthesizes a formal research manuscript in DOCX format. |
| 🚫 `off_topic` | "What is the weather?" | Polite redirection to keep the session focused. |

### 3. Dynamic Domain-Specific Expert Routing
ResearchHelp-AI Analysis System doesn't just categorize the *intent* of your question; it identifies the *domain* you are researching. 
By scanning both your prompt and the retrieved context, the system detects keywords associated with 44 specific disciplines (e.g., `Cybersecurity`, `Maths`, `Deep Learning`, `Computer Networks`, `Biomedical Engineering`). 
When a domain is detected, ResearchHelp-AI-anaylsis-system dynamically injects an overarching, expert-crafted directive for that specific field into the LLM prompt. This forces the model to:
- **Adopt a Domain-Specific Analytical Lens** (e.g., evaluating threat limits for Cybersecurity, analyzing packet limits and latency logic for Networks).
- **Enforce Output Constraints** (e.g., outputting pure LaTeX symbols for Maths, formatting outputs around the SDLC for Software Engineering).

### 4. The IEEE Official Paper Generator
ResearchHelp-AI Analysis System acts as an automated collaborative researcher:
1. **Metadata Collection**: Enter your team names, official emails, college affiliations, and paper title in the **📝 IEEE Paper Metadata** expander within the **💬 Document Chat** tab.
2. **Context Synthesis**: The AI reviews your uploaded documents and your entire chat history.
3. **Scholarly Prompting**: The `IEEE_PAPER_PROMPT` enforces a strict academic structure (Abstract, Keywords, Introduction, Literature Review, Methodology, Results, Conclusion, References).
4. **Professional Output**: Generates an instantly downloadable `IEEE_Paper.docx` formatted to simulate professional publication standards.

### 4. Hybrid Retrieval Engine (Semantic + BM25)
ResearchHelp-AI Analysis System ensures no piece of context is missed by running a dual-channel retrieval system:
- **70% Semantic Search (ChromaDB)**: Finds conceptually relevant passages using `all-mpnet-base-v2` dense embeddings, even if different terminology is used.
- **30% Keyword Search (BM25 Okapi)**: Catches precise, exact-match technical terms that dense embeddings might underrate.
- **Re-Ranking Pipeline**: Merges, deduplicates, and ranks the top 12 chunks for maximum context injection into the LLM.

### 5. Intelligent Topic Segmentation
Documents aren't just split randomly; they are segmented semantically:
- **Cosine Similarity Drops**: Detects topic shifts dynamically when consecutive sentence embeddings drop below a 0.78 similarity threshold.
- **LLM Context Titling**: Automatically generates concise 2-word titles for every semantic segment.
- **Abbreviation-Aware Splitting**: Prevents accidental splits on "Dr.", "e.g.", ensuring complete sentences.

### 6. Auto-Generated Document Insights
The moment your documents are ingested, ResearchHelp-AI Analysis System provides:
- **Document Overview**: A structured, high-level summary of the entire corpus.
- **AI Suggestions**: 5 categorized, actionable research suggestions (Improvement, Innovation, Gap Analysis, Optimization).

### 7. Session Analytics & Complete Transparency
- **Real-Time Dashboards**: Track source usage, topics explored, and queries asked in the sidebar.
- **Expandable Source Cards**: Every AI response includes clickable citations showing exactly which document chunk was used, its relevance score, and the original text.
- **Logic Traces**: View the underlying LLM "chain of thought" to understand *how* it arrived at its conclusions.

---

## 🛠️ Technology Stack

- **Frontend Interface**: [Streamlit](https://streamlit.io/) with custom CSS / theming.
- **Vector Database**: [ChromaDB](https://www.trychroma.com/) (Persistent local storage).
- **AI & ML Models**:
  - LLM Reasoning & Intent: `arcee-ai/trinity-large-preview:free` (via OpenRouter).
  - Embeddings: `sentence-transformers/all-mpnet-base-v2` (768-dim, locally executed).
- **Retrieval Infrastructure**: `rank-bm25` (Okapi algorithm) + ChromaDB native similarity search.
- **Document Parsing Suite**: `PyMuPDF (fitz)` (PDF), `python-docx` (Word), `pytesseract` + `Pillow` (Images), `pandas` (Tables).
- **Multimedia Rendering**:
  - Code visualizer: `Mermaid.js` (Frontend CDN).
  - Text-to-Speech: Web Speech API (Client-side execution).
  - Automated imagery: `Pollinations.ai` (REST Generation).

---

## 📦 Installation & Setup

### Prerequisites
- **Python 3.10+** installed on your system.
- **Git** installed on your system.
- **Tesseract OCR**: Required for extracting text from images and scanned PDFs.
  - **Windows**: Download the installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) (Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`).
  - **macOS**: `brew install tesseract`
  - **Linux**: `sudo apt-get install tesseract-ocr`

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/ResearchHelp-AI-anaylsis-system.git
cd ResearchHelp-AI-anaylsis-system
```

### 2. Set Up a Virtual Environment
It's highly recommended to use a virtual environment to manage dependencies.
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all required Python packages using `pip`.

```bash
pip install -r requirements.txt
```

#### Detailed Requirements Breakdown
The system relies on the following core libraries defined in `requirements.txt`:
- **Web UI & Export**: `streamlit`
- **Document Parsers**: `PyMuPDF` (PDFs), `python-docx` (Word Docs), `pandas` & `openpyxl` (CSV/Excel)
- **Computer Vision (OCR)**: `pytesseract`, `Pillow`
- **NLP & Embeddings**: `sentence-transformers` (MPNet), `scikit-learn` (Cosine Similarity), `nltk` (Sentence Tokenization)
- **Vector Search & Retrieval**: `chromadb` (Semantic DB), `rank-bm25` (Keyword Algorithm)
- **LLM Integration**: `openai` (OpenRouter connectivity), `python-dotenv` (Key management)

### 4. Configure Environment
1. Create a file named `.env` in the root directory of the project.
2. Add your **OpenRouter API Key** (or standard OpenAI API key if modifying the base URL).
   ```env
   OPENROUTER_API_KEY=your_api_key_here
   ```

---

## 🏃‍♂️ Operational Usage

1. **Start the Application**
   ```bash
   streamlit run app.py
   ```

2. **Ingest Research Data**
   - Use the sidebar to upload multiple files (PDFs, Images, Data Sheets).
   - Click **"🚀 Process Documents"**. The system will chunk, embed, and index the content.

3. **Engage with the Insights**
   - Review the auto-generated **📄 Document Overview** and **💡 AI Suggestions** tabs.
   - Use the Text-to-Speech (TTS) buttons to have the summaries read aloud.

4. **Deep Research Chat**
   - Navigate to the **💬 Document Chat** tab.
   - Ask complex technical questions. The Intent Classifier will route your query appropriately.
   - Example: *Ask "Explain the core networking architecture simply"* to trigger the Simple English Deep Analysis Mode.

5. **Generate an Official Publication**
   - Navigate to the **💬 Document Chat** tab and open the **📝 IEEE Paper Metadata** expander.
   - Fill in your team's details.
   - Type in the chat: *"Generate an IEEE research paper based on our analysis."*
   - Click the **Download IEEE Official Paper (.docx)** button attached to the response.

6. **Export Your Session**
   - At the bottom of the sidebar, download your entire analytical session (including analytics, overviews, and chat history) via Word or HTML buttons.

---

## 🔒 Security

This project follows security best practices:

- **Secrets Management**: API keys are stored in `.env` file (not committed to git)
- **Input Sanitization**: User-provided text is sanitized before HTML rendering to prevent XSS
- **File Validation**: File size limits (50MB) and extension validation on uploads
- **Path Traversal Prevention**: Filenames are sanitized to prevent directory traversal attacks

### Production Considerations

For production deployment, consider adding:
- Rate limiting on API calls
- Authentication (e.g., streamlit-authenticator)
- HTTPS/TLS encryption
- Regular dependency updates

---

## 📋 System Testing

Run different tests based on your needs:

### Quick System Diagnostic
```bash
python test_system.py
```
Verifies API connection, ChromaDB, and basic pipeline.

### Full A-Z System Test
```bash
python test_full_system.py
```
Comprehensive test covering document ingestion, hybrid retrieval, intent classification, and export generation.

### Pipeline Integration Test
```bash
python test_pipeline.py
```
Tests the RAG pipeline components.

---
Built with ❤️ and Python.
