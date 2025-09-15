#!/usr/bin/env python3
"""
Simple local test script for BOM2Pic Excel processing functionality.
This bypasses authentication to test core image extraction.
"""
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from excel_processor import process_excel_files

def test_excel_processing():
    """Test the Excel processing functionality."""
    print("🚀 BOM2Pic Local Test")
    print("=" * 50)
    
    # Check if we have any sample Excel files
    test_files_dir = Path("test_files")
    if not test_files_dir.exists():
        print("📁 Creating test_files directory...")
        test_files_dir.mkdir()
        print("   Please add some .xlsx files with images to the 'test_files' directory")
        print("   Then run this script again.")
        return
    
    # Look for Excel files
    excel_files = list(test_files_dir.glob("*.xlsx"))
    if not excel_files:
        print("❌ No .xlsx files found in test_files directory")
        print("   Please add some Excel files with embedded images for testing")
        return
    
    print(f"📊 Found {len(excel_files)} Excel file(s):")
    for file in excel_files:
        print(f"   - {file.name}")
    
    # Get user input for columns
    print("\n🔧 Configuration:")
    image_column = input("Enter the column letter that contains images (e.g., 'A'): ").strip().upper()
    name_column = input("Enter the column letter that contains names/IDs (e.g., 'B'): ").strip().upper()
    
    if not image_column or not name_column:
        print("❌ Both columns are required")
        return
    
    if image_column == name_column:
        print("❌ Image and name columns must be different")
        return
    
    # Process files
    print(f"\n⚡ Processing files...")
    print(f"   Image column: {image_column}")
    print(f"   Name column: {name_column}")
    
    try:
        # Read files
        files_data = []
        for file_path in excel_files:
            with open(file_path, 'rb') as f:
                content = f.read()
                files_data.append((file_path.name, content))
        
        # Process
        zip_buffer, total_images, saved_count, duplicate_count = process_excel_files(
            files_data, image_column, name_column
        )
        
        # Save result
        output_file = Path("bom2pic_test_output.zip")
        with open(output_file, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        # Results
        print(f"\n✅ Processing Complete!")
        print(f"   Total images found: {total_images}")
        print(f"   Images saved: {saved_count}")
        print(f"   Duplicates: {duplicate_count}")
        print(f"   Output file: {output_file.absolute()}")
        
        print(f"\n📦 Extract the ZIP file to see your images and processing report!")
        
    except Exception as e:
        print(f"❌ Error processing files: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_excel_processing()
