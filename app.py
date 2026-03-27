import streamlit as st
import zipfile
import tempfile
import os
import pandas as pd
import docx
import nbformat
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Graceful loading of PDF Support
try:
    import PyPDF2

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Robust Student Project Evaluator", layout="wide")

if 'API_KEY' not in st.secrets:
    st.error("API_KEY not found in Streamlit secrets. Please add it to your secrets.toml file.")
    st.stop()

API_KEY = st.secrets['API_KEY']
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Gemini Client: {e}")
    st.stop()

# RAW DATABASE (Will be sanitized below)
RAW_PROJECT_DATABASE = {
    "Stock Market & Crypto": {
        "Institutional-Grade Equity Research Report": """
            Project: Deep Dive Initiation of Coverage on Tata Motors Ltd.
            Requirements:
            1. Segmental Analysis: Detail JLR, Commercial Vehicles (CV), and Passenger Vehicles (PV/EV). Analyze Porter's Five Forces.
            2. Financial Analysis: 5 years of annual reports, calculate D/E, ROE, ROCE, and Operating Margins.
            3. Valuation: Must include both Sum-of-the-Parts (SOTP) using EV/EBITDA multiples and a 10-year Discounted Cash Flow (DCF) model.
            4. Thesis: Formulate investment thesis, catalysts, and primary risks.
            Final Deliverable: A professional PDF research report (~20-25 pages) and supporting Excel/Google Sheet model with Buy/Hold/Sell recommendation.
        """,
        "Crypto Whitepaper & Tokenomics Deep Dive": """
            Project: Comparative Analysis of Ethereum (ETH) vs. Solana (SOL).
            Requirements:
            1. Protocol Analysis: Compare consensus mechanisms (PoS vs. PoH+PoS), throughput, latency, and decentralization trade-offs.
            2. Tokenomics: Analyze token supply, issuance, inflation/deflation, staking rewards, and gas fees/burns.
            3. Ecosystem Health: Analyze TVL, daily active addresses, transaction counts, DeFi/NFTs.
            Final Deliverable: A professional PDF research report comparing ETH and SOL with a clear long-term outlook and risk assessment.
        """,
        "Pairs Trading Strategy Analysis (Market Neutral)": """
            Project: Identify, analyze, and backtest a pairs trading strategy.
            Requirements:
            1. Pair Identification: Perform correlation and cointegration tests on candidate pairs.
            2. Trading Rules: Construct price spread and define entry/exit rules using z-scores.
            3. Backtesting: Simulate trades using Python (Pandas, NumPy, Statsmodels) and evaluate returns, drawdowns, Sharpe ratio, and win rate.
            Final Deliverable: A detailed analytical report with code (Jupyter Notebook), charts, and performance evaluation.
        """,
        "Building a Crypto Market Fear & Greed Index": """
            Project: Construct a custom Fear & Greed Index using multiple market indicators.
            Requirements:
            1. Component Selection: Select indicators (volatility, momentum, volume, sentiment).
            2. Normalization & Weighting: Normalize indicators and assign weights.
            3. Construction: Combine into a single index and analyze historical behavior.
            Final Deliverable: A fully functional Fear & Greed Index (Excel/Python) with historical interpretation.
        """,
        "Developing and Backtesting a Quantitative Trading Strategy": """
            Project: Design, implement, and backtest a dual moving average crossover strategy.
            Requirements:
            1. Strategy Logic: Implement short-term and long-term moving averages with clear entry (golden cross) and exit (death cross) rules.
            2. Backtesting Engine: Write Python code handling position sizing, transaction costs, and capital tracking.
            3. Evaluation: Analyze cumulative returns, maximum drawdown, Sharpe ratio, and compare against a buy-and-hold benchmark.
            Final Deliverable: Detailed backtesting report including logic, code (Jupyter Notebook), performance charts, and critical assessment.
        """,
        "Options Strategy Modeling – The Bull Call Spread": """
            Project: Model and analyze a Bull Call Spread.
            Requirements:
            1. Strategy Construction: Define long call at lower strike and short call at higher strike.
            2. Payoff Modeling: Calculate net premium, max profit, max loss, and breakeven point.
            3. Visualization: Create payoff diagrams across a range of underlying prices.
            Final Deliverable: A complete options payoff model (Excel/Google Sheets) with charts and written interpretation.
        """,
        "A Deep Dive into a DeFi Protocol and Yield Farming Strategy": """
            Project: In-depth analysis of a DeFi protocol (e.g., Uniswap) and yield strategy.
            Requirements:
            1. Protocol Deep Dive: Analyze liquidity pools, AMMs, and fee structures.
            2. Yield Strategy: Estimate APY from trading fees and incentive rewards.
            3. Risk Analysis: Assess impermanent loss, smart contract vulnerabilities, and regulatory risks.
            Final Deliverable: Comprehensive DeFi research report outlining yield opportunities and risk considerations.
        """,
        "On-Chain Analysis for Predicting Crypto Market Moves": """
            Project: Analyze key on-chain metrics for Bitcoin or Ethereum.
            Requirements:
            1. Metric Selection: Select active addresses, transaction volume, exchange inflows/outflows, and MVRV ratio.
            2. Historical Analysis: Study relationships between metrics and price movements.
            3. Market Thesis: Develop a data-backed market outlook.
            Final Deliverable: Detailed on-chain analysis report with charts and interpretations.
        """,
        "Designing a Multi-Asset Class All-Weather Portfolio": """
            Project: Design a diversified portfolio for stable returns across economic cycles.
            Requirements:
            1. Economic Regime Analysis: Identify inflation, deflation, growth, and recession environments.
            2. Asset Allocation: Allocate across equities, bonds, gold, commodities, and alternatives.
            3. Risk Management: Define rebalancing rules and analyze portfolio volatility/drawdowns.
            Final Deliverable: A formal Investment Policy Statement (IPS) (PDF) and Excel model describing portfolio construction and rationale.
        """
    },

    "Cloud Computing": {
        "Deploying a Secure and Publicly Accessible Virtual Server": """
            Project: Launch a personal blog on a virtual machine (EC2/Compute Engine).
            Requirements:
            1. VM Setup: Launch Linux VM and securely connect via SSH.
            2. Firewall: Open Port 22 (SSH) only to own IP, open Port 80 (HTTP) to 0.0.0.0/0. Allocate a Static/Elastic IP.
            3. Application: Install LAMP stack and deploy WordPress.
            Final Deliverable: A working public URL to the WordPress installation, and a short PDF with screenshots of firewall rules and static IP config.
        """,
        "Building a Resilient Two-Tier Web Application Architecture": """
            Project: Deploy a public web server and private database server.
            Requirements:
            1. Network: Create a custom VPC with 1 Public Subnet and 1 Private Subnet.
            2. Security: Web Tier firewall allows HTTP from internet. Database Tier firewall allows port 3306 ONLY from Web Tier private IP.
            3. Application: Deploy a health check webpage on Web Tier querying the Database Tier.
            Final Deliverable: Public IP displaying "Database Connection: OK", network architecture diagram, and PDF with firewall rule screenshots.
        """,
        "Implementing a Personal Cloud Storage Solution": """
            Project: Secure S3/Cloud Storage bucket for personal files.
            Requirements:
            1. Storage: Create a globally unique bucket and enable "Block all public access".
            2. IAM: Create a custom IAM user/policy with ONLY s3:PutObject, s3:GetObject, s3:ListBucket access to that specific bucket.
            3. Interacting: Upload and list files using CLI and a GUI client (e.g., Cyberduck).
            Final Deliverable: PDF with screenshots of bucket policy blocking public access, the JSON IAM policy, and successful CLI/GUI file uploads.
        """,
        "Building an Auto-Scaling and Load-Balanced Web Application": """
            Project: Deploy an auto-scaling web app behind a load balancer.
            Requirements:
            1. Golden Image: Create an AMI/Custom Image from a configured web server.
            2. Auto-Scaling: Set min 1, desired 1, max 3 instances. Create scaling policies based on CPU utilization (>50% scale out, <20% scale in).
            3. Load Balancer: Route traffic to the ASG and test via stress testing.
            Final Deliverable: Load Balancer public DNS URL, and PDF showing ASG config, CPU spike monitoring graphs, and instance launch/termination history.
        """,
        "Deploying a Scalable Static Website with a CDN": """
            Project: Host a serverless static website via Object Storage and CDN.
            Requirements:
            1. Storage: Upload HTML/CSS/JS to a bucket and enable "static website hosting".
            2. Bucket Policy: Make objects publicly readable.
            3. CDN: Create a CloudFront/Cloud CDN distribution pointing to the bucket origin.
            Final Deliverable: Public CDN URL serving the website, and a PDF explaining cost/scalability benefits with a screenshot of CDN config.
        """,
        "Building a Serverless Data Processing Pipeline": """
            Project: Event-driven pipeline processing simulated tweets.
            Requirements:
            1. Ingestion: Python script sending JSON to SQS/Kinesis.
            2. Processing: Lambda function extracts hashtags and writes to DynamoDB.
            3. Archival: Second Lambda function batches raw tweets to an S3 bucket.
            Final Deliverable: GitHub repo link, architecture diagram, and PDF screenshots showing DynamoDB items and S3 raw files.
        """,
        "Building a Serverless Image Processing API": """
            Project: Lambda function to automatically resize images.
            Requirements:
            1. Storage/IAM: Create `my-uploads` and `my-thumbnails` buckets. Set IAM role for read/write.
            2. Function: Python Lambda (using Pillow layer) triggered by S3 PutObject to resize to 128x128 and save to thumbnails bucket.
            Final Deliverable: Python code file, screenshot of IAM role permissions, and screenshots of source upload and resulting thumbnail.
        """,
        "Building a Simple CI/CD Pipeline for a Web App": """
            Project: Automate deployment to a VM via GitHub Actions.
            Requirements:
            1. Application: Create a basic Node.js app and run it on a free-tier Linux VM.
            2. Workflow: Write a YAML file using `appleboy/ssh-action` to SSH into the VM, pull code, and restart the server on every push to main.
            3. Secrets: Securely store IP, username, and SSH key in GitHub Secrets.
            Final Deliverable: GitHub repo link, the YAML workflow file, and a video/GIF showing a pushed code change updating the live website.
        """,
        "Deploying a Containerized Application with Managed Services": """
            Project: Dockerize a web app and deploy to serverless containers (Cloud Run/Fargate).
            Requirements:
            1. Containerize: Write a Dockerfile for a basic web app and build locally.
            2. Registry: Push image to Amazon ECR or Google Artifact Registry.
            3. Deploy: Deploy image to a managed container service and expose a public port.
            Final Deliverable: GitHub repo with app code + Dockerfile, and the public URL of the live managed container application.
        """,
        "Infrastructure as Code (IaC) with Terraform": """
            Project: Programmatically deploy the two-tier network from Project 2.
            Requirements:
            1. Configuration: Write `.tf` files defining VPC, public/private subnets, Internet Gateway, Route Tables, Security Groups, and two EC2 instances.
            2. Execution: Run `terraform init`, `plan`, and `apply`.
            Final Deliverable: GitHub repo with `.tf` files, detailed README, and screenshots of the `terraform plan` output and created cloud resources.
        """
    },

    "Data Science": {
        "Predicting Customer Churn for a Telecom Company": """
            Project: End-to-end classification model on Telco Customer Churn dataset.
            Requirements:
            1. EDA: Visualizations identifying profiles of churning customers (tenure, contract type).
            2. Feature Engineering: Handle categorical data, scale numerical data, engineer new features (e.g., MonthlyChargesToTenureRatio).
            3. Modeling: Train Logistic Regression, Random Forest, and XGBoost/LightGBM. Evaluate using AUC-ROC, Precision, Recall, Confusion Matrix.
            4. Interpretation: Use SHAP or feature importance to extract top factors.
            Final Deliverable: Comprehensive Jupyter Notebook including EDA, feature engineering, model comparison, and actionable business recommendations.
        """,
        "Customer Segmentation using Clustering for Marketing Strategy": """
            Project: K-Means clustering on Mall Customer Segmentation Data.
            Requirements:
            1. Clustering: Use the "Elbow Method" to find optimal K. Train K-Means model.
            2. Visualization: 2D scatter plot of Annual Income vs. Spending Score colored by cluster.
            3. Persona Creation: Calculate mean stats for each cluster and give them descriptive names.
            Final Deliverable: Jupyter Notebook with Elbow plot, colored cluster visual, Persona Analysis, and specific actionable marketing strategies.
        """,
        "Time Series Forecasting for Retail Sales Prediction": """
            Project: Predict weekly store sales using Walmart dataset.
            Requirements:
            1. EDA & Engineering: Decompose Trend, Seasonality, Residuals. Engineer lag, rolling average, and date-based features.
            2. Modeling: Train SARIMA baseline and LightGBM/XGBoost models.
            3. Evaluation: Walk-forward validation, MAE, RMSE. Generate a 4-week forecast plot with confidence intervals.
            Final Deliverable: A comprehensive Jupyter Notebook with decomposition visuals, model comparisons, and forecast visualizations.
        """,
        "Sentiment Analysis of Product Reviews with NLP": """
            Project: Text classification on Amazon Fine Food Reviews.
            Requirements:
            1. Preprocessing: Robust text cleaning pipeline.
            2. Vectorization: Implement Bag-of-Words and TF-IDF.
            3. Modeling: Train a Logistic Regression or Naive Bayes model.
            Final Deliverable: A well-documented Jupyter Notebook showing data cleaning, vectorization, and model evaluation metrics.
        """,
        "Building a Content-Based Recommendation System for Movies": """
            Project: Recommend similar movies using The Movies Dataset.
            Requirements:
            1. Feature Extraction: Create a "content soup" of relevant metadata.
            2. Similarity Calculation: Use TF-IDF Vectorizer and Cosine Similarity.
            3. Recommendation Function: Create a function returning the top 10 similar movies for a given input.
            Final Deliverable: A working Jupyter Notebook demonstrating the recommendation engine.
        """,
        "Image Classification with Transfer Learning (Cats vs. Dogs)": """
            Project: CNN classifier using pretrained models (VGG16/ResNet50).
            Requirements:
            1. Data Prep: Image resizing, batching, and data augmentation (rotations, flips).
            2. Transfer Learning: Freeze base model, add custom dense head with sigmoid activation.
            3. Fine-Tuning: Train custom head, optionally unfreeze last layers. Evaluate accuracy, precision, recall.
            Final Deliverable: Jupyter Notebook including augmentation setup, transfer learning code, training history plots, and evaluation metrics.
        """,
        "A/B Testing Analysis for a Web Page Redesign": """
            Project: Statistical analysis of control vs treatment groups.
            Requirements:
            1. Setup: Sanity checks, define null/alternative hypotheses, set alpha = 0.05.
            2. Statistics: Calculate conversion rates, perform two-proportion z-test, calculate p-value and confidence interval.
            3. Recommendation: Conclude whether to accept/reject null hypothesis in plain business language.
            Final Deliverable: Jupyter Notebook formally stating hypotheses, statistical calculations, and a definitive, data-backed recommendation.
        """,
        "Building a Simple API for your Machine Learning Model": """
            Project: Wrap a trained model (e.g., Spam Classifier) in a FastAPI backend.
            Requirements:
            1. Serialization: Save trained model and vectorizer using joblib or pickle.
            2. API Creation: Use FastAPI to create a `/predict` endpoint returning JSON predictions and confidence scores.
            Final Deliverable: Project folder with Python FastAPI script, saved model files, requirements.txt, and README explaining how to test locally.
        """,
        "End-to-End MLOps with Experiment Tracking": """
            Project: Instrument a machine learning training script using MLflow.
            Requirements:
            1. Tracking: Wrap training code in `mlflow.start_run()`. Explicitly log hyperparameters, metrics (e.g., RMSLE), and artifacts.
            2. Experimentation: Run script multiple times with different parameters.
            Final Deliverable: Python script with MLflow implementation, and a README with screenshots of the MLflow UI showing experiment comparisons.
        """,
        "The Capstone: Open-Ended Data Science for Social Good": """
            Project: Independent analysis on a social issue (Health, Environment, etc.).
            Requirements:
            1. Define a research question and find a public dataset (World Bank, WHO, etc.).
            2. Execute deep EDA, data cleaning, rich visualizations, and appropriate statistical/ML modeling.
            Final Deliverable: A comprehensive, high-quality Jupyter Notebook or PDF report clearly stating methodology, visualizations, and policy implications.
        """,
        "Automated Invoice Processing and Anomaly Detection": """
            Project: Short analytical project on data parsing and outlier detection.
            Requirements: Build a system to extract data from invoices and detect anomalies.
            Final Deliverable: Code/Notebook showcasing parsing logic and anomaly detection techniques.
        """,
        "Automated Resume Analyzer for Job Portals": """
            Project: Short NLP project extracting skills/experience from unstructured resumes.
            Requirements: Implement NLP and information extraction techniques to parse text.
            Final Deliverable: Code/Notebook showcasing information extraction and data structuring.
        """,
        "Customer Lifetime Value Prediction": """
            Project: Short predictive modeling project forecasting total customer revenue.
            Requirements: Build a predictive model using customer analytics and strategic forecasting.
            Final Deliverable: Predictive model code and strategic forecast insights.
        """,
        "Personalized Email Campaign Optimization": """
            Project: Short marketing analytics project optimizing email timing and content.
            Requirements: Implement A/B testing and personalization algorithms based on user behavior.
            Final Deliverable: Analytical report or notebook demonstrating A/B test results and strategy.
        """,
        "Market Basket Analysis for Upselling/Cross-Selling": """
            Project: Short retail analytics project using association rules.
            Requirements: Apply association rule mining to identify frequently co-occurring purchases.
            Final Deliverable: Code/Notebook identifying pattern recognition and association rules.
        """,
        "Real-Time Public Transport Delay Prediction": """
            Project: Short time-series forecasting using real-time/historical transport data.
            Requirements: Develop a model predicting delays based on streaming/historical data.
            Final Deliverable: Time-series model code and evaluation.
        """,
        "Route Optimization for Delivery Services": """
            Project: Short optimization algorithms/graph theory project.
            Requirements: Create algorithms to determine the most efficient delivery routes to minimize costs/time.
            Final Deliverable: Optimization code and logistical planning report.
        """,
        "Employee Attrition Prediction for HR": """
            Project: Short predictive analytics project on HR data.
            Requirements: Identify employees at risk of attrition and ascertain underlying factors.
            Final Deliverable: Classification model and strategic workforce planning recommendations.
        """,
        "Supply Chain Risk Prediction": """
            Project: Short time-series and risk assessment project.
            Requirements: Develop models to anticipate supply chain disruptions.
            Final Deliverable: Time-series analysis code and resilient strategy report.
        """,
        "Automated Invoice Matching and Fraud Detection": """
            Project: Short rule-based/anomaly detection project.
            Requirements: Implement automated matching of invoices to purchase orders to detect discrepancies.
            Final Deliverable: Code showing data reconciliation and fraud detection logic.
        """,
        "Automated Survey Analysis Tool for Businesses": """
            Project: Short NLP/Sentiment analysis project.
            Requirements: Automatically process and extract insights/sentiment from survey responses.
            Final Deliverable: NLP code demonstrating sentiment analysis on feedback.
        """,
        "Automated Content Tagging for Blogs": """
            Project: Short NLP text classification project.
            Requirements: Automatically assign keywords to blog content based on text characteristics.
            Final Deliverable: Text classification model and content organization logic.
        """
    },

    "Cybersecurity": {
        "ThreatView - A Tiered Threat Intelligence Dashboard": """
            Project: SaaS platform aggregating open-source threat intelligence feeds.
            Requirements:
            1. Backend: Node.js/Python backend with a scheduler fetching data from APIs (AlienVault, PhishTank) storing in PostgreSQL/MongoDB.
            2. Frontend: React dashboard (Chart.js/D3.js) showing top attacking countries, malware, phishing URLs, and a searchable IoC database.
            3. Features: Customizable alerts and weekly PDF summary reporting.
            Final Deliverable: Fully deployed application with a freemium monetization tier system.
        """,
        "PhishScale - Phishing Simulation & Training Platform": """
            Project: SaaS to launch realistic phishing simulation campaigns.
            Requirements:
            1. Dashboard: React interface for campaign management, template library, and target group management.
            2. Backend: Node.js backend integrated with an email provider (SendGrid/AWS SES). Must serve mock landing pages and track clicks/submissions.
            3. Analytics: Real-time tracking of open rates, click rates, and educational landing page redirects.
            Final Deliverable: Deployed application demonstrating campaign creation and metric tracking.
        """,
        "GuardianBox - End-to-End Encrypted File Sharing": """
            Project: Secure file sharing utilizing Web Crypto API.
            Requirements:
            1. Encryption: Implement client-side encryption in React using `crypto.subtle` before upload. Password stays in URL hash.
            2. Features: Password-protected links, disposable links (expiration/download limits).
            3. Backend: Node.js handling encrypted blobs and metadata (stored in S3/B2).
            Final Deliverable: Deployed end-to-end encrypted app where the server cannot read file contents.
        """,
        "BreachAlert - Personal Data Breach Monitoring Service": """
            Project: Service alerting users if emails appear in data breaches.
            Requirements:
            1. Backend: Background jobs (BullMQ/Celery) scanning publicly available breach lists (HIBP API).
            2. Features: Secure user dashboard, automated scheduled scanning, real-time email alerts, and actionable security recommendations.
            3. Security: Hashed user passwords and encrypted sensitive database data.
            Final Deliverable: Deployed application capable of monitoring emails and triggering alerts.
        """,
        "VulnScan Lite - On-Demand Web Vulnerability Scanner": """
            Project: Tool to perform passive security health checks on URLs.
            Requirements:
            1. Backend: Python (requests, BeautifulSoup) checking HTTP headers, secure cookie attributes, basic CMS vulnerabilities, and SSL/TLS config.
            2. Processing: Use a job queue to manage scans asynchronously.
            3. Frontend: React app presenting easy-to-understand report cards with remediation links.
            Final Deliverable: Deployed scanner app with explicit disclaimers regarding authorized usage.
        """,
        "SecureCode Academy - Interactive Secure Coding Platform": """
            Project: E-learning platform teaching developers to fix OWASP Top 10 flaws.
            Requirements:
            1. Frontend: React with a code editor component (Monaco Editor).
            2. Backend: Node.js backend executing submitted code in a secure, isolated "sandboxing" environment. Must be heavily secured against escapes.
            3. Features: Gamified progress, language-specific tracks, team dashboards.
            Final Deliverable: Deployed platform demonstrating an interactive vulnerable-to-secure code challenge.
        """,
        "LogLens - Simplified Security Log Analysis": """
            Project: Web tool parsing web server logs to flag threats.
            Requirements:
            1. Engine: Python backend using regex to parse Apache/Nginx logs and detect SQLi, directory traversal, and brute-force attempts.
            2. Frontend: React dashboard displaying summaries, timelines, and flagged IP addresses. Asynchronous processing for large files.
            Final Deliverable: Deployed application capable of ingesting log files and outputting actionable threat analysis.
        """,
        "DarkWatch - Brand Monitoring for the Dark Web": """
            Project: Isolated tool searching Tor network for brand mentions.
            Requirements:
            1. Engine: Python backend interfacing with Tor to scan curated forums/marketplaces. MUST be heavily isolated from main database.
            2. Features: Keyword management dashboard, findings dashboard (anonymized sources), and high-priority email alerts.
            Final Deliverable: Deployed application architecture prioritizing safety and strict ethical/legal boundaries.
        """,
        "Vaultify - A Secure Web-Based Password Manager": """
            Project: Zero-knowledge architecture password manager.
            Requirements:
            1. Cryptography: React frontend derives key from Master Password (PBKDF2/Argon2) and uses AES-256 to encrypt/decrypt the vault client-side.
            2. Backend: Node.js/Python API storing ONLY hashed passwords for authentication and encrypted vault blobs.
            3. Features: Password generator, 2FA support, secure sharing.
            Final Deliverable: Deployed password manager proving zero-knowledge implementation.
        """,
        "CTF-Builder - A Platform for Creating Capture The Flag Events": """
            Project: SaaS for hosting live CTF cybersecurity competitions.
            Requirements:
            1. Frontend: React apps for Event Organizers (challenge editor, setup) and Participants (challenge viewer, flag submission).
            2. Backend: Node.js with WebSockets (Socket.IO) for a real-time updating scoreboard.
            3. Database: PostgreSQL for core data, Redis for fast scoreboard caching.
            Final Deliverable: Deployed platform demonstrating live event creation, flag submission, and real-time scoring.
        """
    },

    "Web Development": {
        "NicheLink - A Community Platform for Remote Workers": """
            Project: Subscription-based social platform for remote niches.
            Requirements:
            1. Features: Secure auth/profiles, niche community boards, project collaboration posting, and direct private messaging.
            2. Tech Stack: React (Material-UI/Ant Design), Redux/Context API, Node.js + Express.js backend, MongoDB/PostgreSQL, JWT auth.
            Final Deliverable: Fully deployed application (Netlify/Vercel + Heroku) with functional subscription tiers.
        """,
        "Artisan’s Corner - An E-commerce Platform for Handmade Goods": """
            Project: Multi-vendor marketplace for craftspeople.
            Requirements:
            1. Features: Vendor dashboards, product listings, secure shopping cart/checkout, review/rating system.
            2. Integrations: Stripe or PayPal payment gateway API.
            3. Tech Stack: React frontend with state management, Node.js backend managing relational DB (users, products, orders).
            Final Deliverable: Fully deployed e-commerce platform demonstrating multi-vendor product flows and payments.
        """,
        "HabitForge - A Gamified Habit Tracking Application": """
            Project: Habit tracker with points, badges, and social accountability.
            Requirements:
            1. Features: Customizable habit creation, visual progress tracking (Chart.js), gamification elements, and premium data exports.
            2. Tech Stack: Engaging React UI, Node.js API with gamification logic, reliable database for historical tracking.
            Final Deliverable: Deployed habit tracking application with freemium logic.
        """,
        "RecipeBox - A Collaborative Recipe Sharing Platform": """
            Project: Social recipe discovery and organization app.
            Requirements:
            1. Features: Intuitive recipe creation (photos, ingredients), powerful search/filtering, personal digital cookbooks, social following/comments.
            2. Integration: Cloud storage (Cloudinary/S3) for efficient image uploads.
            3. Tech Stack: Clean React UI, Node.js backend.
            Final Deliverable: Deployed collaborative platform with premium meal planner features simulated.
        """,
        "FreelanceFlow - A Project Management Tool for Freelancers": """
            Project: Dashboard merging project management, time tracking, and CRM.
            Requirements:
            1. Features: Project/Task boards, built-in time tracker, simple client CRM, invoice generation, financial dashboard.
            2. Tech Stack: React dashboard with charting libraries, Node.js secure API.
            Final Deliverable: Deployed SaaS tool with functional time tracking and invoice generation.
        """,
        "LocalVibe - A Hyperlocal Event Discovery Platform": """
            Project: Centralized event discovery with map-based UI.
            Requirements:
            1. Features: Searchable event listings, event submission forms, user RSVPs, and personalized algorithmic recommendations.
            2. Tech Stack: React frontend using Leaflet or Google Maps API for geolocation features, Node.js backend.
            Final Deliverable: Deployed platform accurately plotting events on a map interface.
        """,
        "StudySync - A Collaborative Study Platform for Students": """
            Project: Platform featuring virtual study rooms and resource sharing.
            Requirements:
            1. Features: Subject study groups, centralized file repository, peer-to-peer quizzing, and premium tutor marketplace.
            2. Tech Stack: React frontend, Node.js backend using WebSockets (Socket.IO) for virtual study rooms/whiteboards, Cloud storage integration.
            Final Deliverable: Deployed application demonstrating real-time collaborative features.
        """,
        "MindWell - A Simple Mental Wellness Journal": """
            Project: Secure, minimalist digital journaling app.
            Requirements:
            1. Features: Guided journaling prompts, mood tracker with visual charts, guided breathing animations.
            2. Security: Strong focus on data encryption at rest and in transit.
            3. Tech Stack: React frontend, highly secure Node.js backend prioritizing privacy.
            Final Deliverable: Deployed journaling application with secure data handling.
        """,
        "CodeFolio - A Portfolio Builder for Developers": """
            Project: Tool to generate customized developer portfolios.
            Requirements:
            1. Features: Professional template library, easy project integration, custom domain routing, built-in contact forms.
            2. Tech Stack: Dynamic React frontend updating in real-time, Node.js backend managing templates. Output must be fast static sites.
            Final Deliverable: Deployed platform that can successfully generate a shareable portfolio page.
        """,
        "IndieGamer Hub - A Community and Discovery Platform for Indie Games": """
            Project: Marketplace bridging indie developers and players.
            Requirements:
            1. Features: Detailed game pages, developer profiles, community forums, rating systems, curated featured sections.
            2. Integrations: Pull data via External APIs from game stores (Steam/itch.io).
            3. Tech Stack: Visually engaging React frontend, Node.js backend.
            Final Deliverable: Deployed platform demonstrating game discovery and community interaction.
        """
    },

    "AI/ML": {
        "Real-Time Anomaly Detection in Financial Transactions": """
            Project: Unsupervised anomaly detection on highly imbalanced FinTech data.
            Requirements:
            1. Preprocessing: PCA-transformed data analysis and RobustScaler scaling.
            2. Modeling: Implement and compare Isolation Forest and Local Outlier Factor (LOF).
            3. Evaluation: Compute Precision, Recall, F1-score. Tune thresholds to balance catching fraud vs false alarms.
            Final Deliverable: Jupyter Notebook with performance comparison, Precision-Recall curve, and final threshold recommendation.
        """,
        "Image Classification using CNNs (Custom Vision Model)": """
            Project: CNN-based crop disease classifier using Plant Village dataset.
            Requirements:
            1. Data Prep: Resize (224x224), normalize, apply data augmentation.
            2. Architecture: Build baseline CNN (Conv2D -> MaxPool -> Dropout -> Dense). Implement Transfer Learning (VGG16/ResNet50). Use Callbacks.
            3. Evaluation: Confusion Matrix, accuracy curves, prediction visuals.
            4. Deployment: Export .h5 and build a simple Flask web interface.
            Final Deliverable: Jupyter Notebook, Flask app script, and model evaluation report.
        """,
        "Object Detection with YOLOv5 or SSD": """
            Project: Traffic rule enforcement detection (helmets, seatbelts).
            Requirements:
            1. Annotation: Use LabelImg/Roboflow for bounding boxes.
            2. Training: Fine-tune pretrained YOLOv5 weights using PyTorch. Handle augmentation.
            3. Evaluation: mAP@0.5, Precision, Recall, IoU. Generate detection video via OpenCV.
            4. API: Create Flask API `/predict` returning bounding box coordinates.
            Final Deliverable: YOLOv5 training notebook, result visuals, and demo video of real-time detections.
        """,
        "Sentiment Analysis on Twitter Data (NLP)": """
            Project: Classify tweets as Positive/Negative/Neutral.
            Requirements:
            1. NLP Preprocessing: Lowercase, remove URLs/mentions, lemmatize (SpaCy/NLTK).
            2. Modeling: Compare Classical (TF-IDF + Logistic Regression/SVM) vs Deep Learning (Tokenization + Embedding + LSTM/BiLSTM).
            3. Dashboard: Use Plotly/Dash/Streamlit to visualize live tweet streams, pie charts, and trends.
            Final Deliverable: Jupyter Notebook (LSTM/TF-IDF), Streamlit dashboard mockup, and evaluation metrics.
        """,
        "Image Captioning with CNN + LSTM": """
            Project: AI generating natural language captions for images (Flickr8k/30k).
            Requirements:
            1. Preprocessing: Extract image features using VGG16/InceptionV3. Tokenize and pad captions.
            2. Architecture: CNN Encoder (extracts features) + LSTM Decoder (generates words). Implement Teacher Forcing.
            3. Evaluation: Calculate BLEU Score. Show generated vs actual captions.
            4. Interface: Streamlit/Flask app for user uploads.
            Final Deliverable: End-to-end Jupyter Notebook, caption samples, and web app interface script.
        """,
        "Chatbot using Sequence-to-Sequence (Seq2Seq) Model": """
            Project: FAQ and small-talk chatbot using Cornell Movie Dialogs.
            Requirements:
            1. Architecture: Encoder (Embedding+LSTM) and Decoder (Embedding+LSTM). MUST implement Attention Mechanism (Bahdanau/Luong).
            2. Evaluation: Categorical Cross-Entropy, Perplexity, and manual dialogue testing.
            3. Integration: Wrap in Flask/Streamlit.
            Final Deliverable: Jupyter Notebook (Seq2Seq with Attention), trained model, and interface screenshots.
        """,
        "Recommendation System using Collaborative Filtering": """
            Project: Personalized movie recommendations using MovieLens.
            Requirements:
            1. Memory-Based: User-User and Item-Item similarity via Cosine Similarity/Pearson.
            2. Model-Based: Matrix Factorization using SVD or NMF.
            3. Evaluation: Calculate RMSE and Precision@K. Visualize top recommendations.
            Final Deliverable: Jupyter Notebook showing EDA, model building, and RMSE evaluation with sample outputs.
        """,
        "End-to-End AI Project Deployment (Capstone)": """
            Project: Deploy a previously trained model as a production-grade web application.
            Requirements:
            1. Packaging: Export model (.pkl/.h5) and preprocessors.
            2. Backend API: FastAPI/Flask with `/predict` and `/health` routes.
            3. Frontend: Streamlit/Gradio UI handling JSON inputs/file uploads.
            4. Cloud: Containerize using Docker and deploy to AWS EC2/Render/Cloud Run.
            Final Deliverable: Full GitHub repo containing model file, Dockerfile, API script, Frontend script, and detailed README.
        """
    },

    "Finance": {
        "Sell-Side Equity Research Report with DCF & Comps": """
            Project: Initiation of Coverage report on Zomato Ltd.
            Requirements:
            1. Segmental & Moat Analysis: Detail Food Delivery, Hyperpure, Blinkit. Evaluate network effects.
            2. Valuation Model (Excel): Build 10-year 3-statement forecast DCF model. Perform Comparable Company Analysis (EV/Sales, EV/EBITDA).
            3. Thesis: Formulate Buy/Hold/Sell rating, price target, and detail risks & mitigants.
            Final Deliverable: Professional PDF research report (~20-25 pages) and a complete, functional Excel financial model.
        """,
        "Leveraged Buyout (LBO) Model for a Potential PE Target": """
            Project: Build a Paper LBO Model for Apollo Tyres Ltd.
            Requirements:
            1. Assumptions: Purchase price (Market Cap x 1.3), Sources (60% Debt/40% Equity).
            2. Operating Model: 3-statement forecast for 5 years.
            3. Debt Schedule: Link debt, build repayment schedule with cash flow sweeps, handle circular interest logic.
            4. Returns: Calculate IRR (>20% target) and MoM. Build sensitivity tables.
            Final Deliverable: Dynamic, clean Excel model with clear assumptions, debt schedule, returns, and sensitivity analysis.
        """,
        "Mergers & Acquisitions (M&A) Accretion/Dilution Model": """
            Project: Analyze Tata Consumer Products acquiring Bikaji Foods.
            Requirements:
            1. Pro-Forma: Combine standalone income statements into a pro-forma statement.
            2. Adjustments: Adjust for financing effects, synergies, and calculate new share count.
            3. Accretion/Dilution: Compare EPS before and after acquisition.
            Final Deliverable: Detailed Excel M&A model showing standalone projections, pro-forma buildup, and EPS accretion/dilution analysis.
        """,
        "Corporate Restructuring & Turnaround Strategy Proposal": """
            Project: Strategy turnaround deck for Vodafone Idea (Vi).
            Requirements:
            1. Diagnosis: Identify root causes (debt, 5G costs).
            2. Turnaround Strategy: Operational (cost-cutting), Financial (debt moratorium, equity), Strategic (enterprise clients).
            3. Projections: Financial projections showing insolvency vs profitability.
            Final Deliverable: Professional presentation deck (25-30 slides) detailing diagnosis, strategy, and financial projections.
        """,
        "Credit Risk Analysis of a Corporate Borrower": """
            Project: Assess a 500 Cr loan request for SteelCraft Ltd.
            Requirements:
            1. Risk Analysis: Analyze business risk (cyclicality) and financial risk (Debt/EBITDA, Interest Coverage, DSCR).
            2. Projections: Forecast ratios post-loan.
            3. Recommendation: Approve/Decline with specific covenants (e.g., Debt/EBITDA < 3.5x).
            Final Deliverable: Credit Assessment Memorandum (Word/PDF) with risks, ratios, projections, and final recommendation.
        """,
        "Portfolio Management – Performance Attribution Analysis": """
            Project: Decompose a mutual fund manager's return sources.
            Requirements:
            1. Model: Build a Brinson-Fachler attribution model in Excel.
            2. Analysis: Analyze Asset Allocation, Security Selection, and Interaction Effects.
            3. Reporting: Summarize Alpha contributions by sector.
            Final Deliverable: Completed Excel attribution model and a one-page summary report.
        """,
        "Designing the Product Spec for a FinTech Robo-Advisor": """
            Project: Product Requirements Document (PRD) for a Robo-Advisor MVP.
            Requirements:
            1. User Journey: Map signup, risk profiling questionnaire, to portfolio creation.
            2. Features: Define model portfolios based on risk score (Debt/Equity split), design low-fidelity Dashboard wireframes.
            3. Logic: Define operational logic for automatic rebalancing and tax-loss harvesting.
            Final Deliverable: Comprehensive PRD (PDF) including journey maps, risk questions, model definitions, wireframes, and logic specs.
        """,
        "Quantitative Backtesting of a Trading Strategy in Python": """
            Project: Backtest a Relative Strength Momentum strategy on NIFTY 500.
            Requirements:
            1. Logic: Calculate 12-month price momentum. Long top 10%, short bottom 10%, hold 1 month.
            2. Script: Python script (Pandas/backtesting.py/Zipline) using 15 years of daily data.
            3. Evaluation: Analyze CAGR, Max Drawdown, Sharpe Ratio, Alpha.
            Final Deliverable: Fully commented Python script and a Jupyter Notebook/PDF report with performance charts and strategy interpretation.
        """
    },

    "Human Resources": {
        "Designing a Comprehensive Competency Framework": """
            Project: Build a foundational talent architecture for FutureProof Tech.
            Requirements:
            1. Architecture: Define Core, Leadership, and Functional competencies.
            2. Behavioral Anchors: Define observable behaviors across a 4-level proficiency scale.
            3. Integration: Create a library of behavioral interview questions, a performance review template, and a visual Career Ladder.
            Final Deliverable: Professional PDF (20-30 pages) containing the full framework, interview question bank, review template, and career ladder.
        """,
        "Revamping the End-to-End Performance Management Cycle": """
            Project: Transition from annual reviews to Continuous Performance Management.
            Requirements:
            1. Framework: Design annual cadence (Q1 Goal Setting, Q2 Check-in, Q3 Peer Feedback, Q4 Calibration).
            2. Toolkit: Create a Manager's Playbook, an Employee's Guide, and system templates (OKR, 360 Feedback).
            3. Rollout: Define a phased implementation and communication plan.
            Final Deliverable: A zipped toolkit containing strategy presentation, Playbook (PDF), Guide (PDF), templates, and comms plan.
        """,
        "Conducting a Data-Driven Diversity & Inclusion (D&I) Audit": """
            Project: Analyze workforce data to uncover representation gaps.
            Requirements:
            1. Quantitative: Analyze demographic disparities in representation, hiring funnels, promotions, compensation, and attrition.
            2. Qualitative: Design a focus group plan and an anonymous Inclusion Survey.
            3. Strategy: Propose 3-5 SMART D&I initiatives (e.g., blind screening).
            Final Deliverable: A 25-30 slide presentation deck including data visualizations, key findings, and a 12-18 month roadmap.
        """,
        "Developing a Strategic Employee Retention Program": """
            Project: Data-backed retention program to lower voluntary turnover.
            Requirements:
            1. Diagnosis: Analyze exit interviews/surveys to identify turnover drivers and create "at-risk" employee personas.
            2. Program Design: Structure around 4 pillars: Career Growth, Manager Enablement, Recognition & Reward, and Culture & Engagement.
            3. Business Case: Estimate costs and calculate ROI of reducing turnover from 18% to 14%.
            Final Deliverable: Strategic PDF document and presentation deck with full analysis, framework, roadmap, and ROI calculations.
        """,
        "Designing a Scalable New Hire Onboarding Experience": """
            Project: Design a 90-Day Onboarding Journey playbook.
            Requirements:
            1. Mapping: Detail Pre-boarding, Week 1, 30-Day, and 31-90 Day stages.
            2. Resources: Create role-specific checklists, communication templates, Week 1 agendas, and 30-60-90 Day Plan templates.
            3. Measurement: Design a Pulse Survey feedback system and define KPIs (Satisfaction, Productivity, Retention).
            Final Deliverable: An "Onboarding-in-a-Box" zipped toolkit with journey map, checklists, comms drafts, and agendas.
        """,
        "Creating a Data-Backed Compensation and Benefits Philosophy": """
            Project: Define salary structures and total rewards strategy.
            Requirements:
            1. Philosophy: Define Market Position (e.g., 50th/75th percentile), Pay Mix, and Core Principles.
            2. Salary Structure: Create a Salary Band Table for a job family with minimum, midpoint, and maximum calculations.
            3. Benefits: Design an employee survey and propose a Tiered Benefits Package.
            Final Deliverable: Formal Compensation and Benefits Philosophy document (PDF) and presentation deck.
        """,
        "Scoping an Internal Talent Marketplace Platform": """
            Project: Write a PRD for a platform connecting employees to internal "gigs".
            Requirements:
            1. Personas/Stories: Create personas (Employee, Manager, HRBP) and 15-20 user stories.
            2. Wireframes/Specs: Low-fidelity wireframes for Employee Profile, Gig Form, and Search Page.
            3. Non-Functional: Define HRIS integrations and data security protocols.
            Final Deliverable: Polished PRD (PDF, 15-20 pages) covering vision, user stories, feature specs, wireframes, and tech requirements.
        """,
        "Designing an AI-Powered New Hire Onboarding Chatbot": """
            Project: Design logic and PRD for an onboarding chatbot ("Mona").
            Requirements:
            1. PRD: Detail Core Features (FAQs, check-ins), Integrations (Slack/HRIS), Admin Dashboard, and AI capabilities.
            2. Conversation Flow: Map chatbot logic and dialogue for critical paths (IT Support, Benefits) using Decision Trees.
            Final Deliverable: A Product Requirements Document (PRD) and a Diagrammed Conversation Flow Document.
        """,
        "Scoping a Predictive Employee Turnover Analytics Dashboard": """
            Project: PRD for a dashboard identifying turnover risk.
            Requirements:
            1. Data Inputs: Define variables (Tenure, Review Scores, Comp Ratio, etc.).
            2. UI/Wireframes: Design layout including Top Metrics, High-Risk Quadrant, and Root Cause Analysis.
            3. Model Logic: Explain predictive scoring logic (assigning weights to predictors).
            Final Deliverable: Comprehensive PRD (PDF) with data schema, annotated wireframes, user stories, and scoring overview.
        """,
        "Creating the Product Spec for a Real-Time Employee Pulse Survey Tool": """
            Project: PRD for a real-time sentiment survey tool.
            Requirements:
            1. Admin UX: Survey Builder, Audience Targeting, Scheduling.
            2. Employee UX: Delivery Channels (Slack/Email), frictionless 60-second experience.
            3. Analytics UI: Live response tracking, trend visualization, filtering.
            4. Privacy: Define rigid anonymity safeguards (e.g., min 5 respondents).
            Final Deliverable: Detailed PRD (PDF) defining user journeys, dashboard features, analytics logic, and anonymity safeguards.
        """
    },

    "Digital Marketing": {
        "Developing a Full-Funnel Digital Marketing & GTM Strategy": """
            Project: 6-month GTM strategy for D2C brand 'NourishNow'.
            Requirements:
            1. Research: Detailed target personas and a competitive matrix analyzing product, pricing, and UX.
            2. Funnel: Map Awareness (Influencers/Ads), Consideration (Lead Magnet), Conversion (Offers/Retargeting), and Loyalty (Email sequence).
            3. Budget & KPIs: Allocate 10 Lakhs across Meta, Google, Influencers. Define target Impressions, CPL, and CAC.
            Final Deliverable: Detailed GTM Strategy Document & Presentation Deck with personas, competitor matrix, funnel plan, budget, and KPI dashboard.
        """,
        "Designing a Comprehensive Content Marketing & SEO Engine": """
            Project: Long-term content strategy to drive organic acquisition for FinTech 'FinWise'.
            Requirements:
            1. Keywords: Google Keyword Planner research yielding 100 long-tail keywords.
            2. Topic Clusters: Organize into 5 pillars with relevant "spoke" content.
            3. Editorial Calendar: Create a 3-month sheet detailing Date, Format (Blog/Video), Topic, SEO Keyword, and Distribution checklist.
            Final Deliverable: Comprehensive Content Strategy PDF and a 3-Month Editorial Calendar spreadsheet.
        """,
        "Planning & Simulating a Google Ads Search Campaign": """
            Project: Campaign blueprint generating real estate leads in Pune.
            Requirements:
            1. Structure: Define Campaign, Ad Groups (by location), 15-20 Exact/Phrase keywords per group, and 30+ negative keywords.
            2. Copy & UX: Draft 3 responsive headlines and 2 descriptions per group. Define Ad Extensions. Wireframe the landing page.
            3. Budget: Estimate CPCs and project Impressions, Clicks, and Leads based on a 5000/day budget and 4% conversion rate.
            Final Deliverable: Google Ads Campaign Blueprint (PDF) with full structure, ad copy, landing page mock-up, and numerical projections.
        """,
        "Building a Meta (Facebook + Instagram) Paid Ads Funnel": """
            Project: Retargeting and audience segmentation funnel for 'EcoWear'.
            Requirements:
            1. Funnel Mapping: Define Objectives, Creatives, Audiences, and KPIs for TOFU (Reach), MOFU (Traffic), and BOFU (Sales/Retargeting).
            2. Testing & Split: Allocate budget percentages and define exact A/B tests (Creative, CTA, Copy).
            3. Dashboard: Design a reporting template tracking Spend, ROAS, and Cost per Purchase.
            Final Deliverable: Meta Ads Funnel Strategy PDF including structure, creatives outline, audiences, test plan, and KPI dashboard.
        """,
        "Creating an Email Marketing & Automation Flow": """
            Project: Lifecycle automation strategy for an online bookstore.
            Requirements:
            1. Segmentation: Segment users by purchase history, behavior, and engagement.
            2. Automations: Design 3 core flows - Welcome Flow (3 emails), Abandoned Cart Flow (2 emails), Re-engagement Flow (3 emails).
            3. Details: Define trigger logic, email subject lines, copy samples, and target KPIs (Open Rate, Conversion Rate).
            Final Deliverable: Email Automation Blueprint (PDF) containing segmentation logic, flow charts, copy samples, and KPI dashboard.
        """,
        "Planning an Integrated Influencer Marketing Campaign": """
            Project: 30-Day Campaign Playbook for a skincare product launch.
            Requirements:
            1. Identification: Define a tiered strategy (Macro, Micro, Nano) and strict selection criteria (Engagement > 3%, India-based).
            2. Campaign Design: Specify hashtags and exact deliverables per influencer (Reels, Carousels, Stories).
            3. Reporting: Define KPIs (CPE, Sales Conversions) and build a Google Sheets tracking dashboard template.
            Final Deliverable: 30-Day Influencer Campaign Playbook (PDF) with selection framework, campaign plan, deliverables, and tracking dashboard.
        """,
        "Designing a Social Media Brand Identity & 30-Day Content Calendar": """
            Project: Brand guide and calendar for a boutique coffee brand.
            Requirements:
            1. Visual Identity: Define Tone of Voice, Color Palette (HEX codes), Typography, and Imagery Style. Create a Brand Moodboard.
            2. Strategy: Define goals, content pillars, and frequencies for Instagram and LinkedIn.
            3. Content Calendar: 30-day spreadsheet mapping dates, formats, topics, copy, and CTAs. Define engagement tactics and analytics KPIs.
            Final Deliverable: Social Media Brand Identity Guide (PDF), visual Brand Moodboard, and a detailed 30-Day Content Calendar (Excel).
        """,
        "Building a Conversion-Focused Landing Page (UI/UX + Copy)": """
            Project: High-converting landing page wireframe for a Bootcamp.
            Requirements:
            1. Wireframe UX: Must include Hero Section (Headline, Subhead, CTA), Social Proof, Course Overview, Curriculum Breakdown, Instructor Profiles, Pricing, FAQs, and Trust Badges.
            2. Copywriting: Apply best practices (short sentences, benefit-driven, psychological triggers like urgency/social proof).
            Final Deliverable: Landing Page Package including Wireframe (PDF/Figma), Full Copywriting Document, and CTA Strategy Notes.
        """,
        "Creating a Data-Driven Marketing Analytics Dashboard": """
            Project: Consolidated Data Studio/Looker dashboard design.
            Requirements:
            1. Integration: Map data sources (Google Ads, Meta Ads, Shopify, GA4).
            2. Layout: Design Overview Page, Channel Performance Page, and Product/Geography Page.
            3. Metrics: Define ROAS, CPA, AOV and set strict Red/Yellow/Green color coding targets. Define automation reporting schedules.
            Final Deliverable: Marketing Analytics Dashboard Blueprint (PDF) with page wireframes, KPI definitions, and data mapping diagram.
        """,
        "360° Digital Marketing Strategy for a Brand of Your Choice": """
            Project: Capstone comprehensive strategy touching every funnel stage.
            Requirements:
            1. Business Phase: Define Brand Vision, 2 Target Personas, and Competitor Matrix.
            2. Funnel Phase: Apply AIDA framework detailing specific tactics per stage.
            3. Channel Phase: Outline specific plans for Paid Media, Content, Social, Email, and SEO.
            4. Execution Phase: Create a 3-month roadmap, budget breakdown, and KPI table.
            Final Deliverable: Complete 360° Strategy Kit including Strategy Document (PDF), 10-12 slide Client Presentation Deck, and Excel KPI Tracker.
        """
    }
}

# CRITICAL FIX 3: Sanitize Curly Quotes that crash the JSON Tokenizer
PROJECT_DATABASE = {}
for domain, projects in RAW_PROJECT_DATABASE.items():
    PROJECT_DATABASE[domain] = {}
    for proj_name, rubric in projects.items():
        # Replace curly apostrophes and em-dashes with straight ones
        clean_name = proj_name.replace("’", "'").replace("–", "-")
        PROJECT_DATABASE[domain][clean_name] = rubric


# ==========================================
# 2. ROBUST INTELLIGENT FILE PARSERS
# ==========================================
def parse_csv(file_path):
    try:
        df = pd.read_csv(file_path, nrows=20)
        return f"[CSV Data - Top 20 Rows schema]\n{df.to_markdown()}"
    except Exception as e:
        return f"[Error reading CSV: {e}]"


def parse_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"[Error reading DOCX: {e}]"


def parse_pdf(file_path):
    if not PDF_SUPPORT:
        return "[PDF parsing skipped: PyPDF2 library not installed.]"
    try:
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:50]:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text
    except Exception as e:
        return f"[Error reading PDF: {e}]"


def parse_ipynb(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        parsed = []
        for cell in nb.cells:
            if cell.cell_type in ['code', 'markdown']:
                parsed.append(f"--- {cell.cell_type.upper()} CELL ---\n{cell.source}")
        return "\n".join(parsed)
    except Exception as e:
        return f"[Error reading IPYNB: {e}]"


IGNORE_DIRS = {'node_modules', 'venv', 'env', '.git', '.idea', '__pycache__', '.pytest_cache', 'build', 'dist', '.next'}
IGNORE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.sqlite3', '.db', '.exe', '.dll', '.so', '.class', '.pkl',
               '.h5', '.zip', '.tar', '.gz'}


def process_zip_submission(zip_file):
    parsed_submission = {}
    total_chars = 0
    MAX_TOTAL_CHARS = 1_500_000
    MAX_FILE_CHARS = 50_000

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:

            # CRITICAL FIX 1: Iterate the zip manifest directly. NEVER extractall() on 18,000 files!
            for file_info in zip_ref.infolist():
                if file_info.is_dir():
                    continue

                file_path = file_info.filename

                # Check for ignored directories IN the path before doing anything
                path_parts = file_path.replace('\\', '/').split('/')
                if any(part in IGNORE_DIRS or part.startswith('.') for part in path_parts) or '__MACOSX' in file_path:
                    continue

                ext = os.path.splitext(file_path)[1].lower()
                if ext in IGNORE_EXTS:
                    continue

                if total_chars >= MAX_TOTAL_CHARS:
                    parsed_submission["WARNING"] = "OVERALL TEXT LIMIT REACHED."
                    break

                if file_info.file_size > 5 * 1024 * 1024:
                    parsed_submission[file_path] = "[File ignored: Exceeds 5MB limit]"
                    continue

                # Extract ONLY the safe, necessary files to the temp dir
                extracted_path = zip_ref.extract(file_info, temp_dir)

                content = ""
                try:
                    if ext == '.csv':
                        content = parse_csv(extracted_path)
                    elif ext == '.docx':
                        content = parse_docx(extracted_path)
                    elif ext == '.pdf':
                        content = parse_pdf(extracted_path)
                    elif ext == '.ipynb':
                        content = parse_ipynb(extracted_path)
                    else:
                        with open(extracted_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                except UnicodeDecodeError:
                    continue
                except Exception:
                    continue

                if len(content) > MAX_FILE_CHARS:
                    content = content[:MAX_FILE_CHARS] + "\n\n...[CONTENT TRUNCATED]..."

                parsed_submission[file_path] = content
                total_chars += len(content)

    return parsed_submission


def safe_json_parse(response_text):
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:-3].strip()
    elif text.startswith("```"):
        text = text[3:-3].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        safe_text = text[:1500] + "\n\n...[RAW OUTPUT TRUNCATED TO PREVENT CRASH]..."
        st.error(f"Critical JSON Parsing Error: AI Hallucination detected.")
        with st.expander("Show Raw AI Output"):
            st.code(safe_text)
        raise ValueError("Failed to parse AI output into valid JSON.")


# --- PUT THESE CLASSES RIGHT ABOVE identify_projects ---
class IdentifiedProject(BaseModel):
    domain: str
    project_name: str

class IdentifiedProjects(BaseModel):
    projects: list[IdentifiedProject] = Field(description="List of all projects the student attempted.")

# --- REPLACE YOUR CURRENT identify_projects FUNCTION WITH THIS ---
def identify_projects(parsed_submission):
    # Sort files by depth (shortest paths first) so AI sees root files like package.json
    file_list = list(parsed_submission.keys())
    file_list.sort(key=lambda x: x.count('/'))
    important_files = file_list[:60]

    # Extract domains and sanitized project names to show the AI
    project_titles_only = {
        domain: list(projects.keys())
        for domain, projects in PROJECT_DATABASE.items()
    }

    prompt = f"""
    Identify WHICH project(s) the student is attempting based on the highest-level files submitted.
    You MUST match the 'project_name' exactly to one of the titles in the 'Available Projects' list below.

    Available Projects:
    {json.dumps(project_titles_only, indent=2)}

    Root Files Submitted:
    {json.dumps(important_files, indent=2)}
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=IdentifiedProjects, # We use Pydantic here instead of strict Enum
            temperature=0.0
        )
    )
    return safe_json_parse(response.text)


class ProjectEvaluation(BaseModel):
    project_name: str
    status: str = Field(description="Must be 'PASS' or 'REJECT'")
    missing_requirements: list[str] = Field(description="Strict list of missing/failed requirements. Empty if PASS.")
    email_subject: str = Field(description="Subject line for the student email.")
    email_body: str = Field(description="Highly professional email body stating facts.")


class EvaluationResult(BaseModel):
    overall_status: str = Field(description="'PASS' only if ALL attempted projects pass. Otherwise 'REJECT'.")
    evaluations: list[ProjectEvaluation]

class PassProjectEvaluation(BaseModel):
    project_name: str
    status: str = Field(description="Must be 'PASS'")
    suggestions: list[str] = Field(description="Constructive list of suggestions for improvement. Empty if perfectly implemented.")
    email_subject: str = Field(description="Subject line for the student email.")
    email_body: str = Field(description="Highly professional email body stating constructive feedback.")

class PassEvaluationResult(BaseModel):
    overall_status: str = Field(description="Must be 'PASS'.")
    evaluations: list[PassProjectEvaluation]

class ReviewProjectEvaluation(BaseModel):
    project_name: str
    comprehensive_analysis_report: str = Field(description="A highly detailed markdown analysis report covering all aspects of the submission.")

class ReviewEvaluationResult(BaseModel):
    overall_status: str = Field(description="Must be 'REVIEW COMPLETED'.")
    evaluations: list[ReviewProjectEvaluation]


def evaluate_submission(parsed_submission, active_rubrics, mode, additional_instructions=""):
    submission_text = ""
    for filepath, content in parsed_submission.items():
        submission_text += f"\n\n{'=' * 40}\nFILE: {filepath}\n{'=' * 40}\n{content}"

    if mode == "Fail (Strict Audit / Default)":
        system_instruction = """
        You are an elite, hyper-critical technical project auditor. Your ultimate objective is to meticulously scrutinize the submission and find valid, rule-based reasons to REJECT it.
        You do not give the benefit of the doubt. Your default stance is REJECT unless the submission demonstrates absolute perfection against the rubric.

        YOUR RULES:
        1. THE REJECTION DIRECTIVE: Actively search for missing files, superficial work, lack of depth, or ignored edge cases. If a rubric requirement asks for "detailed analysis" and the student provides brief work, you MUST reject it.
        2. THE FAIRNESS DIRECTIVE: To remain fair, you must be completely factual. To justify a rejection, you must explicitly point to the exact rubric requirement that was missed.
        3. ZERO TOLERANCE: If EVEN ONE sub-requirement is missing or incomplete, the status MUST be 'REJECT'. No partial credit.
        4. Generate `email_subject` and `email_body`. The `email_body` MUST contain the comprehensive evaluation report, structured professionally, ready to be sent to the student directly. 

        [EMAIL DRAFT INSTRUCTIONS]
        - Be highly professional, factual, cold, and direct. Start with "Dear Student,".
        - Clearly state the project name and the final outcome (PASSED or REJECTED).
        - Provide a detailed evaluation report WITHIN the email body itself.
        - If REJECTED, strictly list the missing, incomplete, or incorrect requirements as bullet points. Explicitly state *why* based on the rubric.
        - End with "Regards,\nEvaluation Team".
        """
        response_schema = EvaluationResult

    elif mode == "Pass (With Suggestions)":
        system_instruction = """
        You are an encouraging and supportive technical evaluator. Your objective is to thoroughly review the submission and ensure it PASSES, providing constructive feedback.

        YOUR RULES:
        1. THE PASS DIRECTIVE: Ensure the status is explicitly 'PASS'. Do not reject the submission.
        2. CONSTRUCTIVE FEEDBACK: Identify areas where the student can improve, missing features, or edge cases missed, and list them strictly as "suggestions".
        3. Generate `email_subject` and `email_body`. The email body MUST contain your evaluation and the list of suggestions.

        [EMAIL DRAFT INSTRUCTIONS]
        - Be professional, encouraging, and supportive. Start with "Dear Student,".
        - Clearly state the project name and the outcome (PASSED).
        - Provide a detailed evaluation report and your constructive suggestions for improvement WITHIN the email body itself.
        - End with "Regards,\nEvaluation Team".
        """
        response_schema = PassEvaluationResult

    elif mode == "Review Only (Comprehensive Analysis)":
        system_instruction = """
        You are an expert technical reviewer. Your sole objective is to provide a deeply comprehensive analysis report of the student's submission against the provided rubric.

        YOUR RULES:
        1. DO NOT assign a PASS or REJECT status.
        2. DO NOT draft an email.
        3. Produce ONLY a highly detailed, richly formatted Markdown analysis report covering strengths, weaknesses, missing elements, and architectural decisions.
        """
        response_schema = ReviewEvaluationResult

    prompt = f"""
    PROJECT RUBRICS TO ENFORCE:
    {active_rubrics}

    STUDENT SUBMISSION (PARSED FILES):
    {submission_text}
    """

    if additional_instructions.strip():
        prompt += f"\n\nADDITIONAL INSTRUCTIONS FROM REVIEWER:\n{additional_instructions}"

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.1,
            max_output_tokens=8192
        )
    )
    return safe_json_parse(response.text)


# ==========================================
# 4. STREAMLIT DASHBOARD UI
# ==========================================
st.title("⚖️ Strict Student Project Evaluator AI")

# State Management for persistent Chat functionality
if 'eval_history' not in st.session_state:
    st.session_state.eval_history = {}

# Selection Tools
col1, col2 = st.columns([2, 1])
with col1:
    eval_mode = st.radio(
        "Select Evaluation Mode:",
        ["Fail (Strict Audit / Default)", "Pass (With Suggestions)", "Review Only (Comprehensive Analysis)"],
        horizontal=True
    )
with col2:
    additional_instructs = st.text_area("Additional Prompt Instructions (Optional):", height=68,
                                        placeholder="e.g. Focus specifically on database security...")

uploaded_zips = st.file_uploader("Upload Student Submissions (.zip)", type=["zip"], accept_multiple_files=True)

if st.button("Evaluate Submissions") and uploaded_zips:
    # Clear history on new evaluation run
    st.session_state.eval_history = {}

    for zip_file in uploaded_zips:
        st.write(f"### 📂 Processing: {zip_file.name}")

        with st.spinner("Rapidly extracting & filtering core files..."):
            parsed_files = process_zip_submission(zip_file)
            st.caption(f"Successfully processed {len(parsed_files)} valid source files.")

        with st.spinner("Identifying attempted projects..."):
            try:
                identified_data = identify_projects(parsed_files)
                detected_projects = identified_data.get('projects', [])

                if not detected_projects:
                    st.error("Could not match the submitted files to any known project.")
                    continue

                project_names = [p['project_name'] for p in detected_projects]
                st.info(f"**Detected Project(s):** {', '.join(project_names)}")

                active_rubrics = ""
                for p in detected_projects:
                    rubric = PROJECT_DATABASE.get(p['domain'], {}).get(p['project_name'],
                                                                       "Ensure standard requirements are met.")
                    active_rubrics += f"--- RUBRIC FOR: {p['project_name']} ---\n{rubric}\n\n"

            except Exception as e:
                st.error(f"Failed to identify projects. Error: {e}")
                continue

        with st.spinner(f"Executing AI Audit ({eval_mode.split(' ')[0]} Mode)..."):
            try:
                result = evaluate_submission(parsed_files, active_rubrics, eval_mode, additional_instructs)

                # Save data to state for rendering and Chat functionality
                st.session_state.eval_history[zip_file.name] = {
                    'result': result,
                    'parsed_files': parsed_files,
                    'active_rubrics': active_rubrics,
                    'mode': eval_mode,
                    'chat_history': []
                }

            except Exception as e:
                st.error(f"Evaluation failed: {str(e)}")

# ==========================================
# 5. RENDER RESULTS & CHAT ENGINE
# ==========================================

# Display stored results from state (Allows interacting without clearing the screen)
for zip_name, data in st.session_state.eval_history.items():
    result = data['result']
    mode = data['mode']

    st.markdown("---")
    st.write(f"### 📄 Evaluation Results: `{zip_name}`")

    if result.get('overall_status') == 'PASS':
        st.success("✅ **OVERALL STATUS: PASS**")
    elif result.get('overall_status') == 'REJECT':
        st.error("❌ **OVERALL STATUS: REJECTED**")
    else:
        st.info("ℹ️ **OVERALL STATUS: REVIEW COMPLETED**")

    for eval_data in result.get('evaluations', []):
        expander_title = f"Evaluation: {eval_data['project_name']}"
        if 'status' in eval_data: expander_title += f" - {eval_data['status']}"

        with st.expander(expander_title, expanded=True):
            if mode == "Fail (Strict Audit / Default)":
                if eval_data.get('status') == 'REJECT':
                    st.error("**Missing/Failed Requirements Summary:**")
                    for req in eval_data.get('missing_requirements', []): st.write(f"- {req}")
                else:
                    st.success("✅ All core requirements met successfully.")

                st.write("---")
                st.write("📧 **Ready-to-Send Email Draft:**")
                st.text_input("Subject:", eval_data.get('email_subject', ''),
                              key=f"sub_{zip_name}_{eval_data['project_name']}")
                st.text_area("Body:", eval_data.get('email_body', ''), height=400,
                             key=f"body_{zip_name}_{eval_data['project_name']}")

            elif mode == "Pass (With Suggestions)":
                st.warning("💡 **Constructive Suggestions for Improvement:**")
                for req in eval_data.get('suggestions', []): st.write(f"- {req}")

                st.write("---")
                st.write("📧 **Ready-to-Send Email Draft:**")
                st.text_input("Subject:", eval_data.get('email_subject', ''),
                              key=f"pass_sub_{zip_name}_{eval_data['project_name']}")
                st.text_area("Body:", eval_data.get('email_body', ''), height=400,
                             key=f"pass_body_{zip_name}_{eval_data['project_name']}")

            elif mode == "Review Only (Comprehensive Analysis)":
                st.write("📝 **Comprehensive Analysis Report:**")
                st.markdown(eval_data.get('comprehensive_analysis_report', ''))

# AI Chat Box at the very bottom
if st.session_state.eval_history:
    st.markdown("---")
    st.markdown("### 💬 Discuss & Tweak AI Evaluation")

    chat_target = st.selectbox("Select Submission Context to Discuss:", list(st.session_state.eval_history.keys()))
    target_data = st.session_state.eval_history[chat_target]

    # Display Chat History
    for msg in target_data['chat_history']:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if chat_query := st.chat_input("Ask a question about the code, or ask AI to tweak the email/review..."):

        target_data['chat_history'].append({"role": "user", "content": chat_query})
        with st.chat_message("user"):
            st.markdown(chat_query)

        with st.chat_message("model"):
            with st.spinner("AI is thinking..."):
                # Formulate lightweight parsed submission context for Chat API
                submission_text = ""
                for filepath, content in target_data['parsed_files'].items():
                    submission_text += f"\nFILE: {filepath}\n{content[:20000]}"  # Soft truncation to keep Chat snappy

                system_instruction = f"""
                You are assisting an evaluator tweaking or discussing a student project.
                RUBRICS: {target_data['active_rubrics']}
                INITIAL AI EVALUATION RESULT: {json.dumps(target_data['result'], indent=2)}
                """

                # Reconstruct conversation history for GenAI SDK
                chat_contents = []
                chat_contents.append(
                    types.Content(role="user", parts=[
                        types.Part.from_text(text=f"Here is the parsed student submission:\n{submission_text}")])
                )
                chat_contents.append(
                    types.Content(role="model", parts=[
                        types.Part.from_text(text="Context loaded. How can I help you adjust the evaluation?")])
                )

                for msg in target_data['chat_history'][:-1]:  # exclude the one we just appended
                    chat_contents.append(
                        types.Content(role=msg["role"], parts=[types.Part.from_text(text=msg["content"])])
                    )

                chat_contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=chat_query)])
                )

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=chat_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3
                    )
                )

                st.markdown(response.text)
                target_data['chat_history'].append({"role": "model", "content": response.text})