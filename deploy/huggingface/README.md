---
title: HireFlow demo API
emoji: 🟦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: The API behind HireFlow's public demo (fictional jobs only)
---

# HireFlow demo API

The backend of [HireFlow](https://github.com/saksham-eng560/HireFlow)'s public demo: the FastAPI app, its
scheduler and the Chromium that fills forms, in one container. It runs in **demo mode**: applications go
only to a bundled careers site with fictional companies, nothing is really sent, and the data resets every
night and on every restart.

Open the dashboard, not this page: the link is in the repository's README. This Space is deployed from the
repository by `.github/workflows/deploy-space.yml`; don't edit it here.
