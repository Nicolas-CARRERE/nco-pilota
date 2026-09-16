"""
Tests documenting current limitations (to be fixed):

1. Competition deduplication - creates one per game instead of grouping
2. engagements.php redirects - club names with spaces cause 302
"""


def test_competition_creation_current_behavior():
    """
    CURRENT: Creates one competition per game (7592)
    EXPECTED: Group by granular fields (~39 competitions)
    
    Tracking issue: Competition matching query not finding existing
    """
    # Document current behavior
    pass


def test_engagements_redirect_issue():
    """
    CURRENT: Club names with spaces redirect to redirection.php
    EXPECTED: Properly fetch engagements
    
    Tracking issue: URL encoding or session handling needed
    """
    # Document known limitation
    pass
