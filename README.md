# TruthLens

TruthLens is an intelligent fact-finding agent that helps you verify claims and gather information from multiple sources across the web.

## Features

- **Fact Finder Agent**: Automated agent for searching and verifying information
- **Web Scraping**: Integration with Firecrawl API for reliable web content extraction
- **Memory Storage**: Local storage system for persisting search results and findings
- **Structured Data**: Pydantic schemas for type-safe data handling

## Project Structure

```
truthlens/
├── agents/                          # Agent modules
│   ├── __init__.py
│   └── fact_finder/                 # Fact finder agent
│       ├── __init__.py
│       ├── agent.py                 # Main agent implementation
│       ├── tools/                   # Agent tools
│       │   ├── __init__.py
│       │   └── firecrawl_fact_finder.py  # Firecrawl integration
│       └── schemas/                 # Data schemas
│           ├── __init__.py
│           └── fact_finder_schema.py     # Pydantic schemas
├── memory/                          # Memory and storage
│   ├── __init__.py
│   └── local_store.py              # Local file storage
├── main.py                         # Main entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment configuration
└── README.md                       # This file
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/A1THARV/truthlens.git
cd truthlens
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your Firecrawl API key
```

## Configuration

Create a `.env` file in the project root with the following:

```env
FIRECRAWL_API_KEY=your_api_key_here
```

Get your Firecrawl API key from [https://firecrawl.dev](https://firecrawl.dev)

## Usage

Run the main application:

```bash
python main.py
```

### Using the Fact Finder Agent

```python
from agents.fact_finder.agent import FactFinderAgent

# Initialize the agent
agent = FactFinderAgent()

# Run a fact-finding query
result = agent.run(
    query="What is the latest information about climate change?",
    max_results=5
)

# Access the results
print(result.summary)
for source in result.sources:
    print(f"{source.title}: {source.url}")
```

### Using Memory Storage

```python
from memory.local_store import LocalStore

# Initialize storage
store = LocalStore(storage_dir="data")

# Save data
store.save("my_key", {"some": "data"})

# Load data
data = store.load("my_key")

# List all keys
keys = store.list_keys()
```

## Dependencies

- `agent-development-kit`: Framework for building AI agents
- `requests`: HTTP library for API calls
- `pydantic`: Data validation using Python type annotations
- `python-dotenv`: Environment variable management

## Development

To contribute to TruthLens:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or contributions, please open an issue on GitHub.