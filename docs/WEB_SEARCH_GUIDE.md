# Web Search & Browsing Guide

Your personal assistant now has internet access! 🌐

## Overview

The agent can now:
- ✅ Search Google for real-time information
- ✅ Fetch and read webpage content
- ✅ Get current weather for any location
- ✅ Get latest news about any topic
- ✅ Research topics by searching + fetching content

**No browser required** - uses lightweight HTTP requests + HTML parsing.

---

## 5 New Tools Available

### 1. `search_web` - Google Search

Search the internet for any topic and get top results.

**Parameters**:
- `query` (required): Search query
- `num_results` (optional): Number of results (default: 5, max: 10)

**Returns**: List of search results with title, URL, snippet

**Example queries**:
```
User: "Search for Python async tutorials"
Agent: → Calls search_web(query="Python async tutorials", num_results=5)
       → Returns 5 Google search results

User: "Find the latest MacBook Pro reviews"
Agent: → Calls search_web(query="MacBook Pro review 2026")
```

---

### 2. `fetch_webpage` - Extract Page Content

Fetch and extract text content from any webpage URL.

**Parameters**:
- `url` (required): Full URL to fetch

**Returns**: Dict with title, content, summary, URL

**Features**:
- Removes navigation, footer, ads automatically
- Extracts main content intelligently
- Returns clean, readable text
- Max 5000 characters (configurable)

**Example queries**:
```
User: "Read the content from https://example.com/article"
Agent: → Calls fetch_webpage(url="https://example.com/article")
       → Returns full article text

User: "What does this page say?" [provides URL]
Agent: → Fetches and summarizes the page
```

---

### 3. `search_and_fetch` - Combined Search + Fetch

Search Google AND automatically fetch content from top results.

**Parameters**:
- `query` (required): Search query
- `num_results` (optional): Number of results to fetch (default: 3, max: 5)

**Returns**: List of results with search info + full page content

**Best for**: Research, comparisons, deep dives

**Example queries**:
```
User: "Compare M3 vs M4 MacBook Pro"
Agent: → Calls search_and_fetch(query="M3 vs M4 MacBook Pro comparison")
       → Fetches content from top 3 results
       → Synthesizes comprehensive answer

User: "Latest developments in quantum computing"
Agent: → Searches + fetches recent articles
       → Provides detailed summary with sources
```

---

### 4. `get_weather` - Weather Lookup

Get current weather for any location.

**Parameters**:
- `location` (required): City name or location

**Returns**: Current weather information from Google

**Example queries**:
```
User: "What's the weather in Tokyo?"
Agent: → Calls get_weather(location="Tokyo")
       → Returns: "Tokyo: 15°C, Partly cloudy..."

User: "Weather in San Francisco"
Agent: → Immediate weather info
```

---

### 5. `get_news` - Latest News

Get latest news articles about any topic.

**Parameters**:
- `topic` (optional): News topic (default: "latest news")
- `num_results` (optional): Number of articles (default: 5)

**Returns**: List of recent news articles with title, URL, snippet

**Example queries**:
```
User: "Latest tech news"
Agent: → Calls get_news(topic="tech")
       → Returns 5 recent tech news articles

User: "Who won the latest F1 race?"
Agent: → Calls get_news(topic="F1 latest race")
       → Returns recent F1 news with race results
```

---

## Real-World Use Cases

### 1. Dynamic Information

**Before** (without web search):
```
User: "What's the weather in Tokyo?"
Agent: "I don't have access to real-time weather data..."
```

**After** (with web search):
```
User: "What's the weather in Tokyo?"
Agent: → get_weather("Tokyo")
       "Tokyo is currently 15°C with partly cloudy skies.
        Humidity: 60%. Expect light rain this evening."
```

---

### 2. Current Events

**Before**:
```
User: "Who won the latest F1 race?"
Agent: "I don't have access to current race results..."
```

**After**:
```
User: "Who won the latest F1 race?"
Agent: → search_and_fetch("latest F1 race winner 2026")
       "Max Verstappen won the Saudi Arabian GP 2026,
        his 3rd win this season. [Full details from ESPN]"
```

---

### 3. Research & Comparisons

**Before**:
```
User: "Compare M3 vs M4 MacBook Pro"
Agent: [Provides outdated info from training data]
```

**After**:
```
User: "Compare M3 vs M4 MacBook Pro"
Agent: → search_and_fetch("M3 vs M4 MacBook Pro comparison 2026")
       [Fetches latest reviews from The Verge, MacRumors, Apple]
       "Based on recent reviews:
        - M4: 25% faster GPU, new Neural Engine
        - M3: Better value, still excellent performance
        - Pricing: M4 starts at $1,999, M3 at $1,599
        [Sources: The Verge, MacRumors]"
```

---

### 4. Fact-Checking & Updates

**Before**:
```
User: "What's the current price of Bitcoin?"
Agent: [Outdated price from training data]
```

**After**:
```
User: "What's the current price of Bitcoin?"
Agent: → search_web("Bitcoin price now")
       "Bitcoin is currently trading at $68,234 USD
        (as of March 5, 2026, 4:15 PM UTC).
        Source: CoinMarketCap"
```

---

## How It Works Under the Hood

### Architecture

```
User Question
     ↓
LLM decides to use web search tool
     ↓
[Tool: search_web / fetch_webpage / etc.]
     ↓
HTTP Request → Google / Target Website
     ↓
HTML Response
     ↓
BeautifulSoup4 parses HTML
     ↓
Extract clean text content
     ↓
Return to LLM
     ↓
LLM synthesizes answer for user
```

### Technology Stack

- **httpx**: Fast async HTTP client
- **BeautifulSoup4**: HTML parsing and content extraction
- **lxml**: High-performance XML/HTML parser
- **No browser automation**: Pure HTTP + parsing (lightweight!)

---

## Configuration

### Default Settings

Web search is **ENABLED by default**. No configuration needed!

### Optional Configuration (.env)

```bash
# Disable web search entirely
WEB_SEARCH_ENABLED=False

# Change request timeout (default: 10 seconds)
WEB_SEARCH_TIMEOUT=15
```

### Restart Required

After changing `.env`, restart the server:
```bash
./run.sh
```

---

## Limitations & Best Practices

### ✅ Works Great For

- **Static content sites**: News, blogs, documentation, Wikipedia
- **Search results**: Google search works reliably
- **Weather**: Google weather widget
- **Public information**: Anything accessible without login

### ❌ Limitations

1. **No JavaScript rendering**
   - Won't work on React SPAs, dynamic web apps
   - Best for traditional HTML pages

2. **No authentication**
   - Can't access pages behind login
   - No cookie/session management

3. **No CAPTCHA handling**
   - Google may show CAPTCHA if too many requests
   - Respects reasonable usage

4. **Content length limits**
   - Max 5000 characters per page (prevents slowness)
   - Can be increased if needed

5. **Rate limiting**
   - 10 second timeout per request
   - No built-in rate limiting (yet)

### Best Practices

1. **Be specific**: "Weather in Tokyo" better than "weather"
2. **Use search_and_fetch for research**: Gets deeper information
3. **Check sources**: LLM shows URLs, verify if critical
4. **Combine tools**: Search first, then fetch specific pages

---

## Examples by Scenario

### Scenario 1: Planning a Trip

```
User: "I'm planning a trip to Tokyo next week. What's the weather
      forecast and any upcoming events?"

Agent workflow:
1. get_weather("Tokyo") → Current weather
2. search_and_fetch("Tokyo events March 2026") → Upcoming events
3. Synthesizes comprehensive travel advice
```

---

### Scenario 2: Tech Purchase Decision

```
User: "Should I buy the M3 or M4 MacBook Pro for video editing?"

Agent workflow:
1. search_and_fetch("M3 vs M4 MacBook Pro video editing")
2. Analyzes multiple reviews
3. Considers your use case
4. Provides recommendation with sources
```

---

### Scenario 3: Daily News Briefing

```
User: "Give me a briefing on today's top tech news"

Agent workflow:
1. get_news("tech", num_results=10)
2. Categorizes by importance
3. Provides summary with links
```

---

### Scenario 4: Research Assistant

```
User: "Explain how quantum entanglement works, using recent research"

Agent workflow:
1. search_and_fetch("quantum entanglement explained 2026")
2. Fetches content from physics journals, university sites
3. Synthesizes explanation with citations
```

---

## Performance Considerations

### Speed

- **search_web**: ~1-2 seconds
- **fetch_webpage**: ~1-3 seconds per page
- **search_and_fetch**: ~3-8 seconds (searches + fetches 3 pages)
- **get_weather**: ~1-2 seconds
- **get_news**: ~1-2 seconds

### Optimization Tips

1. **Use search_web first** for quick results, then fetch_webpage if needed
2. **Limit num_results** for faster responses
3. **Cache results** (future feature) for repeated queries
4. **Parallel fetching** (future feature) for speed

---

## Troubleshooting

### Problem: "Could not fetch webpage"

**Possible causes**:
- Page requires JavaScript (React app)
- Page behind login/paywall
- Timeout (page too slow)
- 404 / Page doesn't exist

**Solution**:
- Try a different source
- Use search_web to find alternative URLs
- Increase timeout in .env (WEB_SEARCH_TIMEOUT=20)

---

### Problem: "Search returned no results"

**Possible causes**:
- Too specific query
- Google CAPTCHA triggered
- Network issue

**Solution**:
- Broaden search query
- Wait a minute and retry
- Check internet connection

---

### Problem: "Content is truncated"

**Cause**: Page content exceeds 5000 character limit

**Solution**: This is intentional to prevent slowness. The summary provides key information. If you need full content, ask agent to focus on specific sections.

---

## Future Enhancements

Potential additions (not yet implemented):

1. **Result caching** - Cache search results for 5 minutes
2. **Parallel fetching** - Fetch multiple pages simultaneously
3. **Image extraction** - Return image URLs from pages
4. **PDF support** - Fetch and parse PDF documents
5. **Video metadata** - Extract YouTube video info
6. **Rate limiting** - Built-in request throttling
7. **JavaScript rendering** - Optional Playwright integration for SPAs

---

## Comparison with Other Approaches

### vs. Browser Automation (Selenium/Playwright)

| Feature | Our Approach (httpx + BS4) | Browser Automation |
|---------|----------------------------|-------------------|
| **Speed** | Fast (1-3 sec) | Slow (5-15 sec) |
| **Memory** | Lightweight (~50MB) | Heavy (~500MB) |
| **Setup** | Simple (pip install) | Complex (Chrome driver, etc.) |
| **JavaScript** | ❌ No | ✅ Yes |
| **Headless friendly** | ✅ Yes | ⚠️ Requires display |
| **Cost** | Free | Free but resource-intensive |

**Verdict**: Our approach is perfect for 90% of use cases (news, weather, static content). Use browser automation only if you absolutely need JavaScript.

---

### vs. Search APIs (Bing, Google Custom Search)

| Feature | Our Approach | Search APIs |
|---------|--------------|-------------|
| **Cost** | Free | Paid (after free tier) |
| **Setup** | None | API key required |
| **Rate limits** | Soft (Google may CAPTCHA) | Hard limits |
| **Content fetching** | Included | Separate requests |

**Verdict**: Our approach is great for personal use. Use APIs for production/commercial use.

---

## Summary

Your agent now has **real-time internet access** with 5 powerful tools:

1. **search_web** - Find anything on Google
2. **fetch_webpage** - Read any webpage
3. **search_and_fetch** - Deep research
4. **get_weather** - Current weather anywhere
5. **get_news** - Latest news on any topic

**Enabled by default**, lightweight, fast, and terminal-friendly.

Test it now:
```
"What's the weather in San Francisco?"
"Latest AI news"
"Compare M3 vs M4 MacBook Pro"
```

Enjoy your smarter, more capable assistant! 🚀
