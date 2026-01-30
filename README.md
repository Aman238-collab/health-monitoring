# Prescription Reminder System

A backend system that digitizes medical prescriptions using OCR (Tesseract) and LLM (Gemini), extracts medication schedules, and manages reminders via Telegram (simulated logging).

## Features

-   **Prescription Digitization**: Upload images or PDFs of prescriptions.
-   **OCR extraction**: Uses Tesseract (and PyMuPDF for PDFs) to extract raw text.
-   **AI Parsing**: Uses Google Gemini to structure data into medications, dosages, and timings.
-   **Database**: Stores patient history and headers in SQLite.
-   **Reminders**: Background scheduler checking for due medications.
-   **Telegram Integration**: Configured to send reminders (currently in simulation mode, logging to console).

## Prerequisites

-   **Python 3.10+**
-   **Tesseract OCR** installed on your system and added to PATH.
    -   [Windows Installer](https://github.com/UB-Mannheim/tesseract/wiki)
-   **Google Gemini API Key**
-   **Telegram Bot Token** (Optional if using simulation mode)

## Installation

1.  **Clone the repository** (if applicable) or navigate to the project folder.

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Setup**:
    Create a `.env` file in the root directory:
    ```ini
    GEMINI_API_KEY=your_gemini_key_here
    TELEGRAM_BOT_TOKEN=your_telegram_token_here
    ```

## Usage

1.  **Start the Server**:
    ```bash
    uvicorn app.main:app --reload
    ```
    The server runs at `http://127.0.0.1:8000`.

2.  **API Documentation**:
    Visit `http://127.0.0.1:8000/docs` for the interactive Swagger UI.

3.  **Upload a Prescription**:
    -   Endpoint: `POST /api/prescriptions/`
    -   Fields:
        -   `file`: Prescription Image (JPG/PNG) or PDF.
        -   `patient_id`: Unique identifier for the patient.
        -   `telegram_chat_id`: Telegram Chat ID (required for new patients).

## Project Structure

-   `app/api`: FastAPI endpoints.
-   `app/ocr`: Tesseract OCR logic (PDF & Image support).
-   `app/llm`: Gemini agent and prompts.
-   `app/db`: SQLite database models.
-   `app/scheduler`: Background worker for notifications.
-   `app/telegram`: Bot logic.
