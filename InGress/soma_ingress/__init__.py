"""Soma.Ingress - The Senses Layer.

A lightweight, high-performance data capture gateway for the Soma ecosystem.
All external inputs (webhooks, file events, terminal logs) flow through here
before being buffered in the raw_lake table for digestion by InGest.
"""

__version__ = "0.1.0"
__all__ = ["app"]

from .main import app
