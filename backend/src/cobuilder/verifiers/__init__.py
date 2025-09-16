"""
Verifiers package for Co-Builder

Contains verification logic for different build types and outputs.
"""

from .pass1_verifier import verify_pass1_bootable

__all__ = ['verify_pass1_bootable']
