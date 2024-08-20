# Scrounger

This project extracts job listings from company websites using AI-powered analysis.


## Setup

1. Clone the repository
2. Install dependencies:

```sh
pip install requests beautifulsoup4 python-dotenv openai
```

3. Create a `.env` file in the project root and add your API keys:

```sh
OPENAI_API_KEY=your_openai_api_key_here
JINAAI_API_KEY=your_jina_api_key_here
```

4. Run the script:

```sh
python main.py https://example.com --output job_listings.csv
```

Replace `https://example.com` with the company's homepage URL you want to analyze.

## Features

- Automatically finds job listing pages
- Extracts job details using AI
- Saves results to a CSV file
- Caches HTML content to reduce API calls

## Requirements

- Python 3.7+
- OpenAI API key
- Jina AI API key

For more detailed usage and configuration options, please refer to the script's help:

```sh
python main.py --help
```

## Workflow

```mermaid
%%{init: {'theme': 'dark', 'flowchart': {'curve': 'basis'}, 'fontSize': 14px}}%%
flowchart TB
    Start(["`Start`"]) --> CheckCompanyURL{"`Is there another company we want to scrape job ads from?`"}
    CheckCompanyURL -->|No| Exit(["`Exit`"])
    CheckCompanyURL -->|Yes| GetMainPage["`Fetch & save company webpage HTML`"]
    GetMainPage --> FindCareersURL{"`Find careers page URL in HTML`"}
    FindCareersURL -->|Not found| CheckCompanyURL
    FindCareersURL -->|Found| GetCareersPage["`Fetch & save careers page HTML`"]
    GetCareersPage --> FindJobListings{"`Find job listings on careers page`"}
    FindJobListings -->|Not found| FindCareersURL
    FindJobListings -->|Found| ExtractJobURLs["`Extract job listing URLs`"]
    ExtractJobURLs --> CheckJobURL{"`Any job URLs left to process?`"}
    CheckJobURL -->|No| CheckValidJob{"`Was a valid job saved?`"}
    CheckValidJob -->|No| FindCareersURL
    CheckValidJob -->|Yes| CheckCompanyURL
    CheckJobURL -->|Yes| GetJobPage["`Fetch & save job listing HTML`"]
    GetJobPage --> ExtractJobInfo{"`Extract job information`"}
    ExtractJobInfo -->|Failed| CheckJobURL
    ExtractJobInfo -->|Success| SaveJobData["`Save job data & mark as valid`"]
    SaveJobData --> CheckJobURL
```