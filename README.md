# 🚀 BOM2Pic v2.0

**Clean Excel Image Extractor** - Extract unlimited images from Excel files instantly. Perfect for parts catalogs, BOMs, and product listings.

## ✨ Features

- 🎯 **30-Day Free Trial** - Full access for new users
- ⚡ **Lightning Fast** - Extract hundreds of images in seconds
- 📊 **Perfect for Catalogs** - Designed for parts catalogs and BOMs
- 🔒 **Secure & Private** - Files processed securely, nothing stored
- 💰 **Flexible Pricing** - $10/month unlimited or $5/file

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Bootstrap 5 + Vanilla JavaScript
- **Authentication**: Simple email-based with trial management
- **Image Processing**: openpyxl + Pillow
- **User Storage**: JSON-based (ready for database upgrade)

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

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application
python -m app.main
```

Open http://localhost:8000 in your browser.

## 📊 Admin Dashboard

View all users and trial status at: http://localhost:8000/admin

Or use the command line:
```bash
python admin_dashboard.py
```

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
BOM2Pic-v2/
├── app/
│   ├── main.py              # FastAPI application
│   ├── auth.py              # Authentication & user management
│   ├── excel_processor.py   # Core Excel processing logic
│   ├── payment.py           # Payment handling
│   └── static/
│       ├── index.html       # Main web interface
│       ├── styles.css       # Custom styles
│       └── app.js          # Frontend JavaScript
├── requirements.txt         # Python dependencies
├── admin_dashboard.py       # Admin user management
├── BOM2Pic PRD.txt         # Product Requirements Document
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

- User emails stored locally (users.json)
- No files permanently stored
- Processing happens in memory
- Automatic cleanup after processing

## 📈 Scaling Notes

Current implementation uses JSON file storage. For production scaling:

- Replace JSON with PostgreSQL/MySQL
- Add Redis for session management
- Implement proper email notifications
- Add file upload to cloud storage
- Set up monitoring and analytics

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support, email support@bom2pic.com or create an issue in this repository.

---

**Built with ❤️ for parts catalog administrators worldwide**
