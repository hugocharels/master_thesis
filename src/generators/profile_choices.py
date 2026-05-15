"""Shared cooperation-profile choice set for cooperation-aware generators."""

from solver import CooperationLevel

COOP_PROFILE_CHOICES = tuple(level.value for level in CooperationLevel.cooperative_subtypes())
