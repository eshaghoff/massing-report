"""Tests for use group permissions."""

from __future__ import annotations

import pytest

from app.zoning_engine.use_groups import get_permitted_uses


class TestResidentialUseGroups:
    def test_r1_limited_uses(self):
        uses = get_permitted_uses("R1")
        assert uses["residential_allowed"] is True
        assert uses["commercial_allowed"] is False
        assert uses["manufacturing_allowed"] is False

    def test_r7a_residential_and_cf(self):
        uses = get_permitted_uses("R7A")
        assert uses["residential_allowed"] is True
        assert uses["community_facility_allowed"] is True
        assert uses["manufacturing_allowed"] is False


class TestCommercialUseGroups:
    def test_c6_allows_everything(self):
        uses = get_permitted_uses("C6-2")
        assert uses["residential_allowed"] is True
        assert uses["commercial_allowed"] is True
        assert uses["community_facility_allowed"] is True

    def test_c7_amusement_only(self):
        uses = get_permitted_uses("C7")
        assert uses["residential_allowed"] is False
        assert uses["commercial_allowed"] is True


class TestManufacturingUseGroups:
    def test_m1_no_residential(self):
        uses = get_permitted_uses("M1-1")
        assert uses["residential_allowed"] is False
        assert uses["manufacturing_allowed"] is True
        assert uses["commercial_allowed"] is True

    def test_m2_heavy_manufacturing(self):
        uses = get_permitted_uses("M2-1")
        assert uses["residential_allowed"] is False
        assert uses["manufacturing_allowed"] is True
        assert uses["commercial_allowed"] is False

    def test_m3_heaviest(self):
        uses = get_permitted_uses("M3-1")
        assert uses["manufacturing_allowed"] is True
