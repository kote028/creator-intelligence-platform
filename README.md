# Creator Marketplace

An AI-powered creator intelligence and direct sponsorship marketplace. Brands can discover creators using performance metrics, publish campaign briefs, and manage sponsorships. Creators can build a profile, connect social accounts, and respond to offers.

## What’s included

- FastAPI backend with JWT authentication and role-aware creator and brand profiles.
- PostgreSQL schema managed through Alembic migrations.
- Creator discovery, performance rankings, campaign recommendations, social account metrics, campaigns, and sponsorship workflows.
- Responsive browser frontend in `frontend/` with search and filters, saved creators, campaign setup, invitations, profile management, and partnership status actions.
- Creator applications with a proposed rate and message, pending review, and accept/decline actions for brands.
- Local ML semantic creator search and advertising field fit insights, with campaign outcome reports for measured impressions, clicks, conversions, and attributed revenue.

## Requirements

- Python 3.10 or newer
- PostgreSQL 14 or newer
- A modern browser

## Start the API

Create a PostgreSQL database, then configure the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `backend/.env` with your database URL and a long, random `SECRET_KEY`. Set `ALLOWED_ORIGINS` to include the frontend origin. Apply migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs`.

To enable YouTube syncing, enable **YouTube Data API v3** in a Google Cloud project and set `YOUTUBE_API_KEY` in `backend/.env`. Keep this key on the backend; never place it in frontend code. Sync is creator-authenticated at `POST /social-accounts/{account_id}/sync-youtube`. Add the creator’s YouTube `@handle`, channel ID, or channel URL as a YouTube social account first. Sync stores raw public subscriber, total view, and video counts with a `youtube_public` source tag. It does not calculate engagement from sampled videos or mix these public statistics into creator rankings. A daily backend cleanup removes public YouTube snapshots after 30 days. See [YouTube API developer policies](https://developers.google.com/youtube/terms/developer-policies) and [derived metrics and storage policy](https://developers.google.com/youtube/terms/derived-metrics-policy) before enabling this integration for users.

## Creator applications, search, and impact insights

- Creators browse active briefs under **Campaigns** and submit a proposed rate plus an optional application message. A creator can have one application or offer per campaign. New applications remain `pending` until the brand accepts or declines them.
- Brands can invite creators from discovery or review creator applications in **Partnerships**. Brands may report campaign outcomes through impressions, clicks, conversions, and attributed revenue. The creator's private insights aggregate reported outcomes by advertising field.
- `GET /creators/semantic-search?q=...` uses a local TF-IDF plus latent semantic analysis (LSA) model over creator bios, niches, locations, and platforms. It requires no hosted AI service or external text API. The model is fit from the current creator corpus and cached in-process; it is useful for topic retrieval but is not a pretrained language model.
- `GET /creators/me/advertising-insights` compares a creator profile with an advertising field taxonomy and combines that fit with brand-reported campaign results. Fit scores are estimates, not measured ad lift. The application does not store impressions or conversions until the brand submits a report.
- `PUT /sponsorships/{sponsorship_id}/results` is restricted to the campaign-owning brand. Creators and brands participating in the partnership can read the report.

The semantic model uses scikit-learn's `TfidfVectorizer`, dimensionality reduction with `TruncatedSVD`, and cosine similarity. Search relevance depends on the language and coverage of creator profiles; it does not infer actual audience demographics or guarantee advertising outcomes.

## Start the frontend

In a second terminal, from the project root:

```bash
python -m http.server 5173 --directory frontend
```

Open `http://localhost:5173`. By default, the frontend connects to `http://localhost:8000`. To use a different API URL, open the browser console and set:

```js
localStorage.setItem('creator_marketplace_api', 'https://your-api.example.com')
```

Refresh the page after changing the URL. The selected API URL and saved creators stay in this browser; the JWT is stored in local storage and can be cleared by signing out.

## First use

1. Create a brand or creator account from the account menu.
2. Complete the profile in **My profile**. Creator accounts can add social platforms and follower counts; a metric snapshot is recorded when a creator adds an account with a follower count.
3. Brands can create a campaign, discover creators, and send an offer from a creator card.
4. Review offers and update partnership status in **Partnerships**.

Creator discovery uses the public `/creators/rankings` API and requires creator metric snapshots for a creator to appear in rankings. Add metrics through the creator profile account form or the API's `/creator-metrics/` endpoint.

Write operations require a signed-in account with the correct role and ownership of the profile, campaign, or social account. Sponsorship lists and metrics are private to the participating accounts and creator owner, respectively.

## Database

The SQL schema is also available in `database/creator_marketplace.sql`. Alembic is the recommended way to initialize and update a database:

```bash
cd backend
alembic upgrade head
```

## Project layout

```text
backend/       FastAPI app, SQLAlchemy models, API routes, migrations, and tests
database/      SQL schema reference
frontend/      Static responsive marketplace UI
```
