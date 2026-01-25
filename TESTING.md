# Testing Guide

## Mock Mode Testing

To test the bot without making real API calls, use Mock Mode:

### Enable Mock Mode

1. Copy `.env.example` to `.env` if you haven't already:
```bash
cp .env.example .env
```

2. Edit `.env` and set:
```
USE_MOCK_API=true
```

3. Start the bot:
```bash
poetry run python -m src
```

You should see:
```
⚠️ MOCK MODE ENABLED - Using fake data for testing
```

### What Mock Mode Provides

Mock mode gives you **realistic fake data** for all order types:

#### Available Orders (5 orders)
- Psychology Essay - $15
- Economics Research Paper - $25
- Nursing Case Study - $10
- Computer Science Discussion Post - $5
- History Essay - $20

#### Processing Orders (2 orders)
- Literature Essay
- Computer Science Coursework

#### Completed Orders (8 orders)
- Medicine Research Paper
- Business Essay
- Environmental Science Case Study
- Philosophy Discussion Post
- Computer Science Essay
- Physics Research Paper
- Sociology Essay
- Biology Coursework

#### Late Orders (1 order)
- History Assignment (overdue)

#### Revision Orders (1 order)
- Chemistry Lab Report

### Testing Settings

1. Click **⚙️ Settings** button
2. Toggle **Auto-Collection** on/off
3. Click **🎯 Configure Criteria**
4. Test each criterion:

#### Price Range
```
Send: 5 20
Result: Only orders between $5-$20
```

#### Pages
```
Send: 1 5
Result: Only orders 1-5 pages
```

#### Order Types
```
Send: Essay, Research Paper
Result: Only Essays and Research Papers
```

#### Academic Levels
```
Send: College, Master
Result: Only College and Master level
```

#### Subjects
```
Send: Nursing, Psychology
Result: Only Nursing and Psychology orders
```

#### Minimum Deadline
```
Send: 12
Result: Only orders with 12+ hours remaining
```

### Clearing Filters

Send `0 0` for price/pages or `clear` for text fields to remove filters.

### Testing Completed Orders Pagination

1. Click **✅ Completed** button
2. You'll see 3 orders per page (8 total = 3 pages)
3. Use **◀️ Prev** and **Next ▶️** buttons to navigate
4. Old messages are automatically deleted

### Viewing Statistics

Click **📊 Statistics** to see:
- Orders Overview (from mock API)
- AI Workflow Stats (from database)

## Switching Back to Real API

Edit `.env`:
```
USE_MOCK_API=false
```

Restart the bot.

## Mock Data Customization

To customize mock data, edit:
```
src/utils/mock_data.py
```

You can:
- Add more orders
- Change prices, subjects, types
- Modify deadlines
