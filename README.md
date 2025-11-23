## Federal Cannabis Legislation Tracker - All States Edition

A comprehensive real-time tracker for cannabis legislation across all 50 U.S. states plus federal bills, with analysis using the CBDT Framework.

## Features

- **Complete Coverage**: Tracks cannabis bills from all 50 states + federal government
- **Real-time Updates**: Automatically fetches the latest bills from LegiScan API
- **Smart Filtering**: Search and filter by state, status, keywords, and date
- **State-by-State View**: Filter to see specific states or federal-only
- **AI-Powered Analysis**: Links to in-depth CBDT Framework analysis for significant bills
- **Responsive Design**: Beautiful, modern interface that works on all devices
- **Open Source**: Free to use and modify

## Live Demo

Visit the tracker at: [Your GitHub Pages URL]

## ⚠️ Important Notes

### API Rate Limits
LegiScan's free tier provides **30,000 requests per month**. Fetching all 50 states uses approximately:
- **200-500 requests per full scan** (depending on how many bills are found)
- Running daily: ~6,000-15,000 requests/month
- **You're well within limits** for daily updates

### First Run Time
The first time you run the scraper, it will take **10-20 minutes** to fetch all states. This is normal! The scraper includes rate limiting to be polite to the API.

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- LegiScan API key ([Get one here](https://legiscan.com/legiscan))
- Git
- GitHub account

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cannabis-legislation-tracker.git
   cd cannabis-legislation-tracker
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your LegiScan API key**
   
   **Windows (Command Prompt):**
   ```cmd
   set LEGISCAN_API_KEY=your_api_key_here
   ```
   
   **Windows (PowerShell):**
   ```powershell
   $env:LEGISCAN_API_KEY="your_api_key_here"
   ```
   
   **Mac/Linux:**
   ```bash
   export LEGISCAN_API_KEY="your_api_key_here"
   ```

4. **Run the scraper to fetch bills**
   ```bash
   python scraper.py
   ```
   
   ⏱️ **First run will take 10-20 minutes** as it fetches from all 50 states!
   
   You'll see progress like:
   ```
   Fetching bills for Federal...
   ✓ Found 15 bills for Federal
   Fetching bills for Alabama...
   ✓ Found 3 bills for Alabama
   ...
   ```

5. **Test locally**
   
   Open `index.html` in your web browser or use a local server:
   ```bash
   python -m http.server 8000
   ```
   
   Then visit `http://localhost:8000` in your browser.

### Deploying to GitHub Pages

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit - All states tracker"
   git remote add origin https://github.com/yourusername/cannabis-legislation-tracker.git
   git branch -M main
   git push -u origin main
   ```

2. **Enable GitHub Pages**
   - Go to your repository settings
   - Navigate to "Pages" in the left sidebar
   - Under "Source", select "main" branch
   - Click "Save"
   - Your tracker will be live at `https://yourusername.github.io/cannabis-legislation-tracker/`

## Workflow: Adding Analysis to Bills

### 1. Update Bill Data

Run the scraper to fetch new bills (recommend weekly or bi-weekly):
```bash
python scraper.py
```

### 2. Identify Significant Bills

Review `bills.json` to find bills worthy of in-depth analysis:
- Major policy changes (legalization, banking, rescheduling)
- Bills with high potential for passage
- Bills that align with your CBDT Framework insights
- Federal bills (always significant)

### 3. Create Analysis Articles

For significant bills:
1. Write a comprehensive analysis article on silentmajority420.com
2. Apply the CBDT Framework to predict outcomes
3. Publish the article and note its URL

### 4. Link Analysis to Bills

Edit `bills.json` to add your analysis URL:
```json
{
  "state_name": "California",
  "bill_number": "SB 420",
  "title": "Cannabis Tax Reform Act",
  "analysis_url": "https://silentmajority420.com/ca-sb420-analysis"
}
```

### 5. Update the Tracker

Commit and push the updated `bills.json`:
```bash
git add bills.json
git commit -m "Add analysis link for CA SB 420"
git push
```

GitHub Pages will automatically rebuild your site!

## Automation Options

### GitHub Actions (Recommended)

Set up automatic weekly updates:

1. Create `.github/workflows/update-bills.yml`:
   ```yaml
   name: Update Bills Data
   
   on:
     schedule:
       - cron: '0 6 * * 0'  # Run every Sunday at 6 AM UTC
     workflow_dispatch:  # Allow manual trigger
   
   jobs:
     update:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         
         - name: Set up Python
           uses: actions/setup-python@v2
           with:
             python-version: '3.9'
         
         - name: Install dependencies
           run: pip install -r requirements.txt
         
         - name: Run scraper
           env:
             LEGISCAN_API_KEY: ${{ secrets.LEGISCAN_API_KEY }}
           run: python scraper.py
         
         - name: Commit and push if changed
           run: |
             git config --global user.name 'GitHub Action'
             git config --global user.email 'action@github.com'
             git add bills.json
             git diff --quiet && git diff --staged --quiet || (git commit -m "Update bills data [automated]" && git push)
   ```

2. Add your LegiScan API key to GitHub Secrets:
   - Go to repository Settings > Secrets and variables > Actions
   - Add a new secret named `LEGISCAN_API_KEY` with your API key

**Note:** Weekly updates are recommended to stay within API limits and reduce unnecessary runs.

## Project Structure

```
cannabis-legislation-tracker/
├── index.html          # Main HTML page
├── style.css          # Styling and layout
├── app.js             # Frontend JavaScript with state filtering
├── scraper.py         # Python scraper for all 50 states + federal
├── bills.json         # Generated bill data (all states)
├── requirements.txt   # Python dependencies
├── README.md          # This file
└── LICENSE           # MIT License
```

## Customization

### Branding

Update the header and footer in `index.html` to match your brand:
- Change the site title
- Update links to your website
- Modify the color scheme in `style.css`

### Styling

The tracker uses CSS variables for easy theming. Edit these in `style.css`:

```css
:root {
    --primary-color: #2ecc71;  /* Main brand color */
    --secondary-color: #3498db; /* Secondary color */
    --accent-color: #e74c3c;   /* Accent color */
    /* ... more variables ... */
}
```

### State Selection

To track only specific states instead of all 50, edit the `STATES` dictionary in `scraper.py`:

```python
# Example: Only track federal + key states
STATES = {
    'US': 'Federal',
    'CA': 'California',
    'NY': 'New York',
    'FL': 'Florida',
    'TX': 'Texas'
}
```

## Performance Tips

- **First run**: Takes 10-20 minutes for all states
- **Subsequent runs**: 10-20 minutes (checks for new/updated bills)
- **Recommended frequency**: Weekly updates to stay within API limits
- **API requests per run**: ~200-500 depending on bill counts

## Troubleshooting

### "Error: LEGISCAN_API_KEY environment variable not set"
Make sure you've set the environment variable before running the scraper.

### Scraper takes too long
This is normal for the all-states version. The scraper includes rate limiting to be polite to the API. First run: 10-20 minutes.

### Some states show no bills
This is normal. Not all states have active cannabis legislation at all times.

### API rate limit exceeded
If you're running the scraper too frequently, you might hit the 30,000/month limit. Stick to weekly updates.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For questions or issues:
- Open an issue on GitHub
- Visit [silentmajority420.com](https://silentmajority420.com)
- Email: [your contact email]

## Acknowledgments

- LegiScan API for providing comprehensive legislative data
- The CBDT Framework for cannabis market analysis methodology
- The cannabis policy reform community

---

**Built by Silent Majority 420** | [Website](https://silentmajority420.com) | [CBDT Framework](https://silentmajority420.com/cbdt-framework)
