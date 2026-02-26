"""Tests for static map image fetching service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.maps import (
    compute_bbox_from_geometry,
    compute_bbox_from_latlng,
    draw_lot_boundary_on_image,
    draw_lot_diagram_reportlab,
    FT_PER_LAT_DEG,
)


# ──────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────

SAMPLE_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [-73.928, 40.657],
        [-73.927, 40.657],
        [-73.927, 40.658],
        [-73.928, 40.658],
        [-73.928, 40.657],
    ]],
}

# Approximate lot in Brooklyn (roughly 100' x 100')
BROOKLYN_LAT = 40.657573
BROOKLYN_LNG = -73.928352


# ──────────────────────────────────────────────────────────────
# BBOX COMPUTATION
# ──────────────────────────────────────────────────────────────

class TestComputeBboxFromGeometry:
    def test_returns_four_floats(self):
        bbox = compute_bbox_from_geometry(SAMPLE_GEOMETRY)
        assert len(bbox) == 4
        assert all(isinstance(v, float) for v in bbox)

    def test_bbox_contains_geometry(self):
        bbox = compute_bbox_from_geometry(SAMPLE_GEOMETRY, padding_pct=0.0)
        minx, miny, maxx, maxy = bbox
        # The bbox should still be at least as large as the geometry
        # (with minimum extent applied)
        coords = SAMPLE_GEOMETRY["coordinates"][0]
        for coord in coords:
            assert coord[0] >= minx or abs(coord[0] - minx) < 0.001
            assert coord[1] >= miny or abs(coord[1] - miny) < 0.001

    def test_padding_expands_bbox(self):
        bbox_no_pad = compute_bbox_from_geometry(SAMPLE_GEOMETRY, padding_pct=0.0)
        bbox_padded = compute_bbox_from_geometry(SAMPLE_GEOMETRY, padding_pct=0.5)
        # Padded bbox should be larger
        assert bbox_padded[0] <= bbox_no_pad[0]  # minx smaller
        assert bbox_padded[1] <= bbox_no_pad[1]  # miny smaller
        assert bbox_padded[2] >= bbox_no_pad[2]  # maxx larger
        assert bbox_padded[3] >= bbox_no_pad[3]  # maxy larger

    def test_minimum_extent(self):
        """Very small polygon should still produce a visible bbox."""
        tiny = {
            "type": "Polygon",
            "coordinates": [[
                [-73.928, 40.657],
                [-73.928001, 40.657],
                [-73.928001, 40.657001],
                [-73.928, 40.657001],
                [-73.928, 40.657],
            ]],
        }
        bbox = compute_bbox_from_geometry(tiny)
        minx, miny, maxx, maxy = bbox
        # Should have at least 200 ft extent in each direction
        min_deg = 200 / FT_PER_LAT_DEG
        assert (maxx - minx) >= min_deg * 0.9  # Allow some floating point slack
        assert (maxy - miny) >= min_deg * 0.9


class TestComputeBboxFromLatlng:
    def test_returns_four_floats(self):
        bbox = compute_bbox_from_latlng(BROOKLYN_LAT, BROOKLYN_LNG)
        assert len(bbox) == 4
        assert all(isinstance(v, float) for v in bbox)

    def test_center_is_in_bbox(self):
        bbox = compute_bbox_from_latlng(BROOKLYN_LAT, BROOKLYN_LNG)
        minx, miny, maxx, maxy = bbox
        assert minx < BROOKLYN_LNG < maxx
        assert miny < BROOKLYN_LAT < maxy

    def test_larger_radius_larger_bbox(self):
        small = compute_bbox_from_latlng(BROOKLYN_LAT, BROOKLYN_LNG, radius_ft=100)
        large = compute_bbox_from_latlng(BROOKLYN_LAT, BROOKLYN_LNG, radius_ft=1000)
        assert (large[2] - large[0]) > (small[2] - small[0])
        assert (large[3] - large[1]) > (small[3] - small[1])


# ──────────────────────────────────────────────────────────────
# POLYGON OVERLAY
# ──────────────────────────────────────────────────────────────

class TestDrawLotBoundaryOnImage:
    def test_overlay_returns_bytes(self):
        """Draw a polygon on a blank image and verify output is valid."""
        # Create a minimal 10x10 white PNG
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        from io import BytesIO
        img = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        bbox = (-73.929, 40.656, -73.926, 40.659)
        result = draw_lot_boundary_on_image(img_bytes, SAMPLE_GEOMETRY, bbox)
        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify result is a valid PNG
        result_img = Image.open(BytesIO(result))
        assert result_img.size == (100, 100)

    def test_overlay_larger_than_original(self):
        """The overlaid image should be different from the original."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        from io import BytesIO
        img = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        bbox = (-73.929, 40.656, -73.926, 40.659)
        result = draw_lot_boundary_on_image(img_bytes, SAMPLE_GEOMETRY, bbox)
        # The overlaid result should be different from the blank white image
        assert result != img_bytes

    def test_empty_coordinates_returns_original(self):
        """If geometry has no coordinates, return original image."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        from io import BytesIO
        img = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        empty_geom = {"type": "Polygon", "coordinates": [[]]}
        bbox = (-73.929, 40.656, -73.926, 40.659)
        result = draw_lot_boundary_on_image(img_bytes, empty_geom, bbox)
        assert result == img_bytes


# ──────────────────────────────────────────────────────────────
# REPORTLAB FALLBACK
# ──────────────────────────────────────────────────────────────

class TestDrawLotDiagramReportlab:
    def test_with_geometry(self):
        """Should produce a Drawing from GeoJSON geometry."""
        d = draw_lot_diagram_reportlab(geometry=SAMPLE_GEOMETRY, lot_area=10000)
        assert d is not None
        assert d.width > 0
        assert d.height > 0

    def test_with_dimensions(self):
        """Should produce a Drawing from lot dimensions (no geometry)."""
        d = draw_lot_diagram_reportlab(
            geometry=None,
            lot_area=5000,
            lot_frontage=50,
            lot_depth=100,
        )
        assert d is not None
        assert d.width > 0

    def test_with_yards(self):
        """Should produce a Drawing with yard setbacks."""
        d = draw_lot_diagram_reportlab(
            geometry=None,
            lot_area=5000,
            lot_frontage=50,
            lot_depth=100,
            rear_yard=30,
            front_yard=10,
            side_yards=True,
            side_yard_width=8,
        )
        assert d is not None

    def test_no_data(self):
        """Should produce a 'not available' Drawing with no geometry or dimensions."""
        d = draw_lot_diagram_reportlab(geometry=None)
        assert d is not None


# ──────────────────────────────────────────────────────────────
# ASYNC IMAGE FETCHING (mocked)
# ──────────────────────────────────────────────────────────────

class TestFetchSatelliteImage:
    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """Should return None when ESRI times out and Google key is not set."""
        import httpx

        with patch("app.services.maps.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.services.maps.settings") as mock_settings:
                mock_settings.google_maps_api_key = ""

                from app.services.maps import fetch_satellite_image
                result = await fetch_satellite_image(
                    BROOKLYN_LAT, BROOKLYN_LNG, SAMPLE_GEOMETRY,
                )
                assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        """Should return None on non-200 response."""
        with patch("app.services.maps.httpx.AsyncClient") as mock_client_class:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.headers = {}

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.services.maps.settings") as mock_settings:
                mock_settings.google_maps_api_key = ""

                from app.services.maps import fetch_satellite_image
                result = await fetch_satellite_image(
                    BROOKLYN_LAT, BROOKLYN_LNG, SAMPLE_GEOMETRY,
                )
                assert result is None


class TestFetchStreetMapImage:
    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """Should return None when all sources fail."""
        import httpx

        with patch("app.services.maps.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.services.maps.settings") as mock_settings:
                mock_settings.google_maps_api_key = ""

                from app.services.maps import fetch_street_map_image
                result = await fetch_street_map_image(
                    BROOKLYN_LAT, BROOKLYN_LNG, SAMPLE_GEOMETRY,
                )
                assert result is None


# ──────────────────────────────────────────────────────────────
# INTEGRATION TEST (hits real ESRI — skip in CI)
# ──────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_esri_satellite_real():
    """Integration test: actually fetch from ESRI (requires network)."""
    from app.services.maps import fetch_satellite_image
    result = await fetch_satellite_image(
        BROOKLYN_LAT, BROOKLYN_LNG, SAMPLE_GEOMETRY,
    )
    # May be None if ESRI is down, but should not raise
    if result is not None:
        assert isinstance(result, bytes)
        assert len(result) > 1000  # Should be a real image


@pytest.mark.integration
@pytest.mark.asyncio
async def test_esri_street_real():
    """Integration test: actually fetch street map from ESRI."""
    from app.services.maps import fetch_street_map_image
    result = await fetch_street_map_image(
        BROOKLYN_LAT, BROOKLYN_LNG, SAMPLE_GEOMETRY,
    )
    if result is not None:
        assert isinstance(result, bytes)
        assert len(result) > 1000
