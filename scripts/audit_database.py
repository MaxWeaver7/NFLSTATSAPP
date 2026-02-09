#!/usr/bin/env python3
"""Database audit script to check what data exists in Supabase."""

import os
import sys
sys.path.insert(0, '/Users/maxweaver/FantasyAppTest/NFLAdvancedStats')

from src.database.supabase_client import SupabaseClient, SupabaseConfig
from src.utils.env import load_env

load_env()

def main():
    cfg = SupabaseConfig.from_env()
    sb = SupabaseClient(cfg)
    
    print("=" * 60)
    print("DATABASE AUDIT REPORT")
    print("=" * 60)
    
    # 1. Games by season and postseason status
    print("\n📅 GAMES BY SEASON + POSTSEASON STATUS:")
    games = sb.select("nfl_games", select="season,week,postseason", limit=5000)
    from collections import defaultdict
    game_counts = defaultdict(lambda: {"regular": 0, "postseason": 0, "weeks": set()})
    for g in games:
        key = g["season"]
        if g.get("postseason"):
            game_counts[key]["postseason"] += 1
        else:
            game_counts[key]["regular"] += 1
        game_counts[key]["weeks"].add(g.get("week"))
    
    for season in sorted(game_counts.keys(), reverse=True):
        info = game_counts[season]
        weeks = sorted(info["weeks"])
        print(f"  {season}: {info['regular']} regular, {info['postseason']} postseason | Weeks: {min(weeks)}-{max(weeks)}")
    
    # 2. Advanced stats coverage
    print("\n📊 ADVANCED STATS COVERAGE:")
    for table in ["nfl_advanced_receiving_stats", "nfl_advanced_rushing_stats", "nfl_advanced_passing_stats"]:
        try:
            rows = sb.select(table, select="season,week,postseason", limit=5000)
            by_season = defaultdict(lambda: {"regular": 0, "postseason": 0, "weeks": set()})
            for r in rows:
                s = r["season"]
                if r.get("postseason"):
                    by_season[s]["postseason"] += 1
                else:
                    by_season[s]["regular"] += 1
                by_season[s]["weeks"].add(r.get("week"))
            
            print(f"\n  {table}:")
            for season in sorted(by_season.keys(), reverse=True):
                info = by_season[season]
                weeks = sorted(info["weeks"]) if info["weeks"] else [0]
                print(f"    {season}: {info['regular']} regular rows, {info['postseason']} postseason | Weeks: {min(weeks)}-{max(weeks)}")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")
    
    # 3. Injuries
    print("\n🏥 INJURIES:")
    try:
        injuries = sb.select("nfl_injuries", select="player_id,status,injury_date", limit=100)
        print(f"  Total injury records: {len(injuries)}")
        if injuries:
            statuses = defaultdict(int)
            for inj in injuries:
                statuses[inj.get("status") or "Unknown"] += 1
            for status, count in sorted(statuses.items(), key=lambda x: -x[1])[:5]:
                print(f"    {status}: {count}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # 4. Betting odds
    print("\n💰 BETTING ODDS:")
    try:
        odds = sb.select("nfl_betting_odds", select="game_id,vendor,spread_home_value", limit=500)
        print(f"  Total odds records: {len(odds)}")
        if odds:
            vendors = defaultdict(int)
            for o in odds:
                vendors[o.get("vendor") or "Unknown"] += 1
            for vendor, count in sorted(vendors.items(), key=lambda x: -x[1]):
                print(f"    {vendor}: {count}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # 5. Player props  
    print("\n🎯 PLAYER PROPS:")
    try:
        props = sb.select("nfl_player_props", select="game_id,prop_type,vendor", limit=500)
        print(f"  Total prop records: {len(props)}")
        if props:
            prop_types = defaultdict(int)
            for p in props:
                prop_types[p.get("prop_type") or "Unknown"] += 1
            for pt, count in sorted(prop_types.items(), key=lambda x: -x[1])[:10]:
                print(f"    {pt}: {count}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # 6. Team season stats (defensive)
    print("\n🛡️ TEAM SEASON STATS:")
    try:
        team_stats = sb.select("nfl_team_season_stats", select="team_id,season,opp_passing_yards_per_game,def_pass_epa:stats_json->>def_pass_epa", limit=100)
        print(f"  Total team season stat records: {len(team_stats)}")
        seasons = set(t.get("season") for t in team_stats)
        print(f"  Seasons covered: {sorted(seasons, reverse=True)}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # 7. Team standings
    print("\n🏆 TEAM STANDINGS:")
    try:
        standings = sb.select("nfl_team_standings", select="team_id,season,wins,losses,playoff_seed", limit=100)
        print(f"  Total standings records: {len(standings)}")
        seasons = set(s.get("season") for s in standings)
        print(f"  Seasons covered: {sorted(seasons, reverse=True)}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # 8. Check for model predictions tables
    print("\n🤖 MODEL PREDICTION TABLES:")
    for table in ["model_predictions_week18", "model_predictions_week18_cushion", "model_predictions_week18_receptions"]:
        try:
            rows = sb.select(table, select="player_id,player_name,pred_yards", limit=5)
            print(f"  {table}: {len(rows)} sample rows")
            if rows:
                print(f"    Example: {rows[0].get('player_name')} - pred: {rows[0].get('pred_yards')}")
        except Exception as e:
            print(f"  {table}: Not found or empty")
    
    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
