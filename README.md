<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# AI-Powered Cold Calling Sales Agent

Welcome to the AI-Powered Cold Calling Sales Agent repository! This project implements an intelligent phone agent capable of conducting natural-sounding sales conversations, analyzing customer responses in real-time, and converting leads into sales opportunities.

## Overview

This AI Sales Agent is a full-stack intelligent sales system designed to seamlessly integrate into existing sales pipelines. The system leverages advanced natural language processing, voice synthesis, and real-time analytics to create personalized and effective cold calling experiences.

The agent can:

- Initiate outbound calls to potential customers
- Conduct natural, flowing conversations
- Adapt its approach based on customer responses
- Provide personalized product recommendations
- Schedule follow-up actions and store conversation insights


## Features

### Voice Intelligence

- Real-time speech-to-text processing
- Natural-sounding text-to-speech using Eleven Labs
- Dynamic conversation flow with contextual understanding
- Emotion and sentiment analysis during calls


### Business Intelligence

- Customer profile integration and enrichment
- Product matching based on detected customer needs
- Objection handling with adaptive responses
- Conversion optimization through continuous learning


### Technical Capabilities

- Scalable architecture supporting concurrent calls
- MongoDB integration for data persistence
- Secure API handling with environment variable protection
- Flask-based backend for robust request handling
- Frontend dashboard for call monitoring and analytics


## System Architecture

The system is built with a modular architecture that allows for easy scaling and component replacement:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Twilio Voice   │◄────┤  Flask Backend  │◄────┤  OpenAI LLM     │
│  Integration    │     │  Controller     │     │  Processing     │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │                 │              │
         └──────────────┤  MongoDB Data   │◄─────────────┘
                        │  Storage        │
                        │                 │
                        └─────────────────┘
```


## Getting Started

### Prerequisites

- Python 3.8 or higher
- MongoDB instance (planned for future implementation)
- Twilio account
- OpenAI API key
- Eleven Labs API key


### Installation

1. Clone the repository:

```bash
git clone https://github.com/electrify-7/AI-Agent.git
cd AI-Agent
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure your environment variables:
    - Copy the `.env.example` file to `.env`
    - Fill in all required API keys and configuration values

### Configuration

The system is configured through environment variables in the `.env` file:

```
# Flask Configuration
SECRET_KEY=your_secret_key
APP_PUBLIC_URL=your_public_url  

# Twilio API Credentials
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=your_twilio_number

# Database Configuration
MONGO_URI=your_mongodb_connection_string
DATABASE_NAME=your_database_name

# OpenAI API Credentials
OPENAI_API_KEY=your_openai_api_key

# Eleven Labs API Credentials
ELEVENLABS_API_KEY=your_elevenlabs_api_key
VOICE_ID=your_selected_voice_id

# Company Details
COMPANY_NAME="Enter Company Name"
COMPANY_BUSINESS="Enter company business description"
COMPANY_PRODUCTS_SERVICES="Enter product/service descriptions"
CONVERSATION_PURPOSE="Enter the primary goal of sales conversations"
AISALESAGENT_NAME="Enter Agent Name"
```


## Usage

### Starting the Server

Run the Flask application:

```bash
python app.py
```

The server will start on the default port (5000) unless configured otherwise.

### Making Test Calls

1. Ensure your Twilio webhook URLs are properly configured to point to your deployed application
2. Use the Twilio console to initiate test calls or integrate with the API
3. Monitor call logs and conversation transcripts in the frontend dashboard

### Frontend Dashboard

The project includes a basic frontend dashboard that allows you to:

- View ongoing and completed calls
- Access conversation transcripts
- Analyze call performance metrics
- Manage agent configurations

Note: The frontend is currently a basic implementation. Database integration and advanced analytics features are planned for future development.

## API Endpoints

The system exposes several API endpoints:


| Endpoint | Method | Description |
| :-- | :-- | :-- |
| `/call/incoming` | POST | Handles incoming call webhooks from Twilio |
| `/call/status` | POST | Processes call status updates |
| `/transcribe` | POST | Converts speech to text for processing |
| `/generate-response` | POST | Creates AI responses based on conversation context |
| `/text-to-speech` | POST | Converts text responses to natural speech |

## Customization

### Agent Personality

Modify the agent's personality and conversation style by updating the prompt templates in the configuration files. The system supports different personas for various sales contexts.

### Product Information

Update the `COMPANY_PRODUCTS_SERVICES` environment variable with detailed product information to enable the agent to provide accurate recommendations and answers.

### Conversation Flows

The conversation logic can be customized by modifying the AI prompt templates and conversation handlers in the codebase.

## Security

This system handles sensitive customer information and requires proper security measures:

- All API keys should be kept secure in environment variables
- Implement proper authentication for API endpoints
- Ensure GDPR and other regulatory compliance for call recording and data storage
- Regularly rotate API keys and access credentials


## Troubleshooting

### Common Issues

1. **Voice quality issues**: Check Eleven Labs configuration and voice selection
2. **Slow response times**: Optimize OpenAI API calls and implement caching
3. **Call connection failures**: Verify Twilio credentials and webhook configurations
4. **Database connection errors**: Check MongoDB connection string and network access

## Future Development

- Complete MongoDB integration for data persistence
- Enhanced analytics dashboard with call performance metrics
- Multi-agent support for different product lines
- Integration with CRM systems for lead management
- Advanced conversation analytics and insights


## Contact

For questions or support, please open an issue in the GitHub repository or contact the project maintainers.

---

*This AI Sales Agent is designed to augment human sales teams, not replace them. Always ensure compliance with local regulations regarding automated calling systems and disclosure requirements.*

