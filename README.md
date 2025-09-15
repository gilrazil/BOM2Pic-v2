# 🚀 BOM2Pic v2.0

**Clean Excel Image Extractor** - Extract unlimited images from Excel files instantly. Perfect for parts catalogs, BOMs, and product listings.

## ✨ Features

- 🎯 **30-Day Free Trial** - Full access for new users
- ⚡ **Lightning Fast** - Extract hundreds of images in seconds
- 📊 **Perfect for Catalogs** - Designed for parts catalogs and BOMs
- 🔒 **Secure & Private** - Files processed securely, nothing stored
- 💰 **Flexible Pricing** - $39 Lifetime Deal, $10/month unlimited, or $5/file

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Bootstrap 5 + Vanilla JavaScript
- **Authentication**: Simple email-based with trial management
- **Image Processing**: openpyxl + Pillow
- **User Storage**: SQLite database with persistent storage

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/BOM2Pic-v2.git
cd BOM2Pic-v2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Quick setup (recommended)
./scripts/setup-dev.sh

# OR Manual setup:
cp .env.example .env
# Edit .env with your configuration
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

## 📊 Admin Dashboard

View all users and trial status:
- **Web**: http://localhost:8000/admin?admin_key=bom2pic_admin_2024
- **CLI**: `python scripts/admin_dashboard.py`

## 🔧 Configuration

### Environment Variables (.env)
```env
# Clerk Authentication (optional - for advanced auth)
CLERK_PUBLISHABLE_KEY=your_key_here
CLERK_SECRET_KEY=your_secret_here

# PayPal (for payments)
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_client_secret
PAYPAL_ENVIRONMENT=sandbox

# App Settings
MAX_UPLOAD_MB=20
BASE_URL=http://localhost:8000
```

## 📁 Project Structure

```
BOM2Pic-Fresh/
├── app/                     # Main application
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application with all routes
│   ├── auth.py              # SQLite-based user management
│   ├── excel_processor.py   # Core Excel processing logic
│   ├── payment.py           # PayPal integration
│   └── static/              # Frontend assets
│       ├── index.html       # Homepage with signup/trial
│       ├── ltd-deal.html    # Lifetime Deal landing page
│       ├── styles.css       # Enhanced responsive styles
│       ├── robots.txt       # SEO crawler instructions
│       └── sitemap.xml      # SEO sitemap
├── scripts/                 # Development & admin tools
│   ├── admin_dashboard.py   # SQLite admin dashboard
│   ├── main_test.py         # Test mode server
├── tests/                   # Test files and data
│   ├── test_local.py        # Local testing script
│   └── test_files/          # Sample Excel files for testing
├── data/                    # Database and persistent data
│   └── users.db             # SQLite user database
├── assets/                  # Static assets (logos, images)
│   └── logo-color.png       # BOM2Pic logo
├── docs/                    # Documentation
│   └── product-requirements.txt # Product Requirements Document
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🎯 How It Works

1. **User Signs Up** - Enter email, get instant 30-day trial
2. **Upload Excel Files** - Drag & drop .xlsx files with images
3. **Select Columns** - Choose image column and name column
4. **Process & Download** - Get organized ZIP with all images

## 💡 Use Cases

- **Parts Catalogs** - Extract product images for e-commerce
- **BOM Management** - Organize component images
- **Inventory Systems** - Bulk image extraction
- **Product Listings** - Prepare images for websites

## 🔒 Privacy & Security

- User data stored in SQLite database (users.db)
- No files permanently stored
- Processing happens in memory
- Automatic cleanup after processing

## 📈 Scaling Notes

Current implementation uses SQLite. For production scaling:

- Migrate SQLite to PostgreSQL/MySQL
- Add Redis for session management
- Implement proper email notifications
- Add file upload to cloud storage
- Set up monitoring and analytics

## 🚀 Deployment

### Development
```bash
./scripts/setup-dev.sh    # Setup local environment
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Render)
```bash
./scripts/deploy-prod.sh   # Deploy to production
```

**Environment Separation:**
- **Localhost**: Uses `data/users.db`, sandbox PayPal, debug mode
- **Production**: Uses `/opt/render/project/data/users.db`, live PayPal, secure keys

## 🤝 Contributing

1. Work on localhost with development environment
2. Test thoroughly with `./scripts/setup-dev.sh`
3. Deploy to production with `./scripts/deploy-prod.sh`
4. Render auto-deploys from `main` branch

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support, email support@bom2pic.com or create an issue in this repository.

---

**Built with ❤️ for parts catalog administrators worldwide**
