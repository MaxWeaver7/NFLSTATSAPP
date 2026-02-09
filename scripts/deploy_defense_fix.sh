#!/bin/bash
# =============================================================================
# Deploy Fixed Smash Views to Supabase
# =============================================================================
#
# This script drops the existing views and recreates them with fixed defense
# ranking logic.
#
# Usage:
#   ./deploy_defense_fix.sh
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set in environment
#   - psql or Supabase CLI installed
# =============================================================================

set -e

echo "🔧 Deploying Defense Logic Fix to Supabase..."
echo ""

# Check if we're in the right directory
if [ ! -f "supabase/view_qb_smash_scores.sql" ]; then
    echo "❌ Error: Must run from NFLAdvancedStats directory"
    exit 1
fi

echo "📋 Steps to deploy:"
echo "1. Open Supabase Dashboard → SQL Editor"
echo "2. Copy and paste the following SQL:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat << 'EOF'
-- Drop existing views
DROP VIEW IF EXISTS public.model_qb_smash CASCADE;
DROP VIEW IF EXISTS public.model_wr_smash CASCADE;
DROP VIEW IF EXISTS public.model_rb_smash CASCADE;

-- Now execute each view file in order:
-- 1. view_qb_smash_scores.sql
-- 2. view_wr_smash_scores.sql
-- 3. view_rb_smash_scores.sql
EOF
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "3. Then copy the contents of each view file and execute:"
echo "   - supabase/view_qb_smash_scores.sql"
echo "   - supabase/view_wr_smash_scores.sql"  
echo "   - supabase/view_rb_smash_scores.sql"
echo ""
echo "4. Verify with test query:"
echo ""
cat << 'EOF'
SELECT player_name, opp_pass_ypg, opp_def_rank_pct, pass_funnel_score
FROM model_qb_smash 
WHERE season = 2025 AND week = 17 
ORDER BY smash_score DESC LIMIT 5;
EOF
echo ""
echo "✅ Expected: Higher YPG (worse defense) = higher pass_funnel_score"
echo ""
echo "📚 For full details, see: DEFENSE_LOGIC_FIX.md"



