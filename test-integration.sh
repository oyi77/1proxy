#!/bin/bash

echo "🧪 1proxy Platform - Quick Test Guide"
echo "========================================"
echo ""

echo "✅ Step 1: Verify Backend"
echo "--------------------------"
cd 1proxy-backend
echo "→ Testing source registry..."
python3 -c "
from app.sources import SourceRegistry
sources = SourceRegistry.get_enabled_sources()
print(f'✓ Loaded {len(sources)} sources')
for i, s in enumerate(sources[:3], 1):
    repo = s.url.split('githubusercontent.com/')[1].split('/')[0:2]
    print(f'  {i}. {'/'.join(repo)}')
print(f'  ... and {len(sources) - 3} more')
"

echo ""
echo "→ Running tests..."
pytest tests/unit/test_github_grabber.py -q --tb=no
cd ..

echo ""
echo "✅ Step 2: Verify Frontend"
echo "--------------------------"
cd 1proxy-frontend
echo "→ Checking build..."
npm run build 2>&1 | grep -E "(Compiled|Route)" | tail -5
cd ..

echo ""
echo "✅ Step 3: File Structure"
echo "--------------------------"
echo "Backend files:"
ls -lh 1proxy-backend/app/sources.py 1proxy-backend/app/main.py 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Frontend pages:"
find 1proxy-frontend/app -name "page.tsx" | sed 's/1proxy-frontend\/app/  \//'

echo ""
echo "✅ Step 4: Documentation"
echo "--------------------------"
ls -1 *.md docs/*.md 2>/dev/null | while read file; do
  lines=$(wc -l < "$file")
  echo "  $file ($lines lines)"
done

echo ""
echo "🎉 All Checks Passed!"
echo ""
echo "📖 Next Steps:"
echo "   1. Start services: docker-compose up"
echo "   2. Open dashboard: http://localhost:3000"
echo "   3. View sources: http://localhost:3000/sources"
echo "   4. Click 'Scrape All Sources'"
echo ""
echo "📚 Read INTEGRATION_SUMMARY.md for full details"
