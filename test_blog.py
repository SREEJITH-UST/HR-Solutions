#!/usr/bin/env python
"""
Test script to verify blog RSS feed fetching functionality
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_solution.settings')
django.setup()

# Now we can import Django modules
import feedparser
import requests
from datetime import datetime
import re

def test_rss_feeds():
    """Test RSS feed fetching from various HR sources"""
    print("Testing HR RSS Feeds...")
    print("=" * 50)
    
    hr_sources = [
        {
            'name': 'HR Dive',
            'feeds': ['https://www.hrdive.com/feeds/']
        },
        {
            'name': 'BambooHR Blog',
            'feeds': ['https://www.bamboohr.com/blog/feed/']
        },
        {
            'name': 'HR Technologist',
            'feeds': ['https://www.hrtechnologist.com/feed/']
        }
    ]
    
    total_articles = 0
    
    for source in hr_sources:
        print(f"\n📰 Testing {source['name']}:")
        for feed_url in source['feeds']:
            try:
                print(f"   Fetching: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                if hasattr(feed, 'entries') and feed.entries:
                    print(f"   ✅ Found {len(feed.entries)} articles")
                    
                    # Show first 2 articles
                    for i, entry in enumerate(feed.entries[:2]):
                        title = getattr(entry, 'title', 'No title')
                        url = getattr(entry, 'link', '#')
                        
                        # Parse published date
                        try:
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                pub_date = datetime(*entry.published_parsed[:6])
                                pub_str = pub_date.strftime('%B %d, %Y')
                            else:
                                pub_str = "Date unknown"
                        except:
                            pub_str = "Date unknown"
                        
                        print(f"      {i+1}. {title[:80]}...")
                        print(f"         📅 {pub_str}")
                        print(f"         🔗 {url}")
                        total_articles += 1
                else:
                    print(f"   ❌ No entries found or feed error")
                    if hasattr(feed, 'bozo_exception'):
                        print(f"      Error: {feed.bozo_exception}")
                        
            except Exception as e:
                print(f"   ❌ Error fetching from {feed_url}: {str(e)}")
    
    print(f"\n📊 Summary: Successfully fetched {total_articles} articles")
    print("=" * 50)

def test_direct_blog_view():
    """Test the blog view function directly"""
    print("\nTesting Blog View Function...")
    print("=" * 50)
    
    try:
        from hr_app.views import blog_view, determine_category
        from django.http import HttpRequest
        from django.test import RequestFactory
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/blog/')
        
        print("📝 Calling blog_view function...")
        response = blog_view(request)
        
        print(f"✅ Response status: {response.status_code}")
        print(f"✅ Response type: {type(response)}")
        
        # Test category determination
        print("\n🏷️  Testing category determination:")
        test_cases = [
            ("AI Revolution in HR", "Discover how artificial intelligence is transforming"),
            ("Remote Work Strategies", "Best practices for managing remote teams"),
            ("Employee Wellness Programs", "Mental health initiatives in workplace")
        ]
        
        for title, desc in test_cases:
            category = determine_category(title, desc)
            print(f"   '{title}' → {category}")
            
    except Exception as e:
        print(f"❌ Error testing blog view: {str(e)}")

if __name__ == "__main__":
    print("🚀 NextGenHR Blog Testing Script")
    print("Testing real-time blog functionality...")
    
    test_rss_feeds()
    test_direct_blog_view()
    
    print(f"\n✨ Testing complete!")
    print("📖 The blog should now display real-time HR articles from multiple sources.")
    print("🌐 Visit http://localhost:8000/blog/ to see the live blog!")
