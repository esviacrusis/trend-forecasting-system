################################################################################################
# Module    :   Ingestion for Vogue Images
# Author    :   Eric S. Viacrusis
# Date      :   April 1, 2026
#
# UPDATES
# April 1   :   This module saves the image files to AWS S3 bucket instead of local storage. It uses the S3Client class from aws_s3.py to handle the upload process.
# April 4   :   Add how to insert into postgres
################################################################################################



# ============================================================
# End-to-End Color Vision Pipeline Framework
# ============================================================
#
# 1. Input
#    - Load Vogue runway image
#
# 2. Garment Detection (PyTorch)
#    - Run garment detection / segmentation model
#    - Output:
#         * bounding boxes
#         * segmentation masks
#
# 3. Apply Mask
#    - Keep only garment pixels
#    - Remove background / non-garment regions
#
# 4. Color Conversion
#    - Convert garment pixels from RGB to LAB
#
# 5. Clustering
#    - Apply KMeans clustering
#    - Extract dominant garment colors
#
# 6. Output Raw Colors
#    - Store:
#         * LAB values
#         * HEX values
#         * percentage proportion of each color
#
# 7. Standardization
#    - Map extracted colors to standardized color references
#    - Output:
#         * color_id
#         * color family (blue, red, neutral, etc.)
#
# 8. Save to DB
#    - Insert results into garment_colors table
#
# ============================================================



"""
cv_pipeline.py

End-to-End Color Vision Pipeline
--------------------------------
Flow:
1. Load Vogue runway image
2. Run garment detection / segmentation model
3. Apply mask to keep garment pixels only
4. Convert RGB -> LAB
5. Cluster dominant colors with KMeans
6. Produce raw color outputs (LAB, HEX, proportion)
7. Standardize to canonical colors
8. Save results to PostgreSQL garment_colors table

Notes:
- This is a starter framework meant to be practical and extendable.
- The garment detection function is written as a placeholder so you can
  connect your PyTorch model later.
- The database insert assumes a table like:
    garment_colors(
        garment_id UUID,
        rank INT,
        hex TEXT,
        rgb_r INT,
        rgb_g INT,
        rgb_b INT,
        lab_l REAL,
        lab_a REAL,
        lab_b REAL,
        percent REAL,
        color_family TEXT,
        mapped_color_id BIGINT
    )
"""

from __future__ import annotations

import db # your database connection module
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

import cv2
import numpy as np
import psycopg2
from psycopg2.extensions import connection as PGConnection
from sklearn.cluster import KMeans

# ============================================================
# Database Connection
# ============================================================







# ============================================================
# Configuration
# ============================================================

MIN_MASK_PIXELS = 500
DEFAULT_K_COLORS = 3


# ============================================================
# Data Classes
# ============================================================

@dataclass
class DetectionResult:
    garment_id: str
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    mask: np.ndarray                  # 2D binary mask, same height/width as image
    category: str = "garment"
    confidence: float = 1.0


@dataclass
class DominantColor:
    rank: int
    rgb: tuple[int, int, int]
    lab: tuple[float, float, float]
    hex_code: str
    percent: float
    mapped_color_id: int | None
    color_family: str


# ============================================================
# Image Loading
# ============================================================

def load_image(image_path: str) -> np.ndarray:
    """
    Load image with OpenCV and convert BGR -> RGB.
    """
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return image_rgb


# ============================================================
# Garment Detection / Segmentation
# ============================================================

def detect_garments_pytorch(image_rgb: np.ndarray) -> list[DetectionResult]:
    """
    Placeholder for your PyTorch garment detection / segmentation model.

    Replace this with your actual model inference.

    Expected output:
    - one DetectionResult per garment
    - each result has:
        * garment_id
        * bbox
        * mask
        * category
        * confidence

    Current behavior:
    - returns one full-image mask as a fallback so the pipeline can run.
    """
    h, w, _ = image_rgb.shape
    full_mask = np.ones((h, w), dtype=np.uint8)

    return [
        DetectionResult(
            garment_id=str(uuid.uuid4()),
            bbox=(0, 0, w, h),
            mask=full_mask,
            category="full_look",
            confidence=0.50,
        )
    ]


# ============================================================
# Masking
# ============================================================

def extract_masked_pixels(image_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Return Nx3 RGB pixels from masked garment region.
    """
    if mask.ndim != 2:
        raise ValueError("Mask must be 2D.")

    if mask.shape[:2] != image_rgb.shape[:2]:
        raise ValueError("Mask and image dimensions do not match.")

    binary_mask = (mask > 0).astype(np.uint8)
    pixels = image_rgb[binary_mask == 1]

    if len(pixels) < MIN_MASK_PIXELS:
        raise ValueError(
            f"Masked region too small for reliable clustering: {len(pixels)} pixels"
        )

    return pixels


# ============================================================
# Color Conversion
# ============================================================

def rgb_pixels_to_lab(rgb_pixels: np.ndarray) -> np.ndarray:
    """
    Convert Nx3 RGB pixels to Nx3 LAB using OpenCV.

    OpenCV LAB output:
    - L in [0, 255]
    - a in [0, 255]
    - b in [0, 255]

    We convert to more standard ranges:
    - L scaled roughly to [0, 100]
    - a shifted by -128
    - b shifted by -128
    """
    rgb_pixels_uint8 = rgb_pixels.astype(np.uint8).reshape(-1, 1, 3)
    lab_pixels = cv2.cvtColor(rgb_pixels_uint8, cv2.COLOR_RGB2LAB).reshape(-1, 3)

    lab_pixels = lab_pixels.astype(np.float32)
    lab_pixels[:, 0] = lab_pixels[:, 0] * (100.0 / 255.0)
    lab_pixels[:, 1] = lab_pixels[:, 1] - 128.0
    lab_pixels[:, 2] = lab_pixels[:, 2] - 128.0

    return lab_pixels


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """
    Convert RGB tuple to HEX string.
    """
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_lab_single(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """
    Convert a single RGB tuple to LAB tuple.
    """
    arr = np.array([[rgb]], dtype=np.uint8)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)[0, 0].astype(np.float32)
    l = float(lab[0] * (100.0 / 255.0))
    a = float(lab[1] - 128.0)
    b = float(lab[2] - 128.0)
    return (l, a, b)


# ============================================================
# Clustering
# ============================================================

def cluster_dominant_colors(
    rgb_pixels: np.ndarray,
    n_colors: int = DEFAULT_K_COLORS,
) -> list[dict[str, Any]]:
    """
    Cluster dominant colors from garment pixels using KMeans on LAB space.

    Returns a list of raw color dicts ordered by descending proportion:
    [
        {
            "rank": 1,
            "rgb": (r, g, b),
            "lab": (l, a, b),
            "hex_code": "#AABBCC",
            "percent": 0.52
        },
        ...
    ]
    """
    if len(rgb_pixels) < n_colors:
        raise ValueError("Not enough pixels for requested number of clusters.")

    lab_pixels = rgb_pixels_to_lab(rgb_pixels)

    model = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    labels = model.fit_predict(lab_pixels)

    raw_colors: list[dict[str, Any]] = []
    total = len(labels)

    for cluster_idx in range(n_colors):
        cluster_mask = labels == cluster_idx
        cluster_rgb = rgb_pixels[cluster_mask]

        if len(cluster_rgb) == 0:
            continue

        mean_rgb = np.mean(cluster_rgb, axis=0)
        mean_rgb_tuple = tuple(int(round(x)) for x in mean_rgb.tolist())

        mean_lab = rgb_to_lab_single(mean_rgb_tuple)
        percent = float(np.sum(cluster_mask) / total)

        raw_colors.append(
            {
                "rgb": mean_rgb_tuple,
                "lab": mean_lab,
                "hex_code": rgb_to_hex(mean_rgb_tuple),
                "percent": percent,
            }
        )

    raw_colors.sort(key=lambda x: x["percent"], reverse=True)

    for idx, item in enumerate(raw_colors, start=1):
        item["rank"] = idx

    return raw_colors


# ============================================================
# Standardization
# ============================================================

def get_color_family(rgb: tuple[int, int, int]) -> str:
    """
    Very simple heuristic for color family.
    Replace with your formal color lexicon or canonical mapping logic later.
    """
    r, g, b = rgb

    if max(rgb) < 40:
        return "black"
    if min(rgb) > 215:
        return "white"
    if abs(r - g) < 15 and abs(g - b) < 15:
        return "neutral"

    if r >= g and r >= b:
        if g > 120 and b < 100:
            return "orange"
        if b > 100:
            return "pink"
        return "red"

    if g >= r and g >= b:
        if r > 140 and b < 100:
            return "yellow"
        return "green"

    if b >= r and b >= g:
        if r > 120:
            return "purple"
        return "blue"

    return "neutral"


def map_to_standard_color(
    rgb: tuple[int, int, int],
    color_reference: list[dict[str, Any]],
) -> tuple[int | None, str]:
    """
    Map RGB color to nearest canonical color using LAB distance.

    color_reference format:
    [
        {
            "color_id": 1,
            "color_name": "Cobalt Blue",
            "color_family": "blue",
            "lab_l": 45.0,
            "lab_a": 10.0,
            "lab_b": -50.0
        },
        ...
    ]
    """
    if not color_reference:
        return None, get_color_family(rgb)

    target_lab = np.array(rgb_to_lab_single(rgb), dtype=np.float32)

    best_color_id: int | None = None
    best_family = get_color_family(rgb)
    best_distance = float("inf")

    for ref in color_reference:
        ref_lab = np.array(
            [ref["lab_l"], ref["lab_a"], ref["lab_b"]],
            dtype=np.float32,
        )
        dist = float(np.linalg.norm(target_lab - ref_lab))

        if dist < best_distance:
            best_distance = dist
            best_color_id = int(ref["color_id"])
            best_family = str(ref.get("color_family", best_family))

    return best_color_id, best_family


def standardize_colors(
    raw_colors: list[dict[str, Any]],
    color_reference: list[dict[str, Any]],
) -> list[DominantColor]:
    """
    Convert raw clustered colors into standardized DominantColor objects.
    """
    standardized: list[DominantColor] = []

    for item in raw_colors:
        mapped_color_id, family = map_to_standard_color(
            rgb=item["rgb"],
            color_reference=color_reference,
        )

        standardized.append(
            DominantColor(
                rank=item["rank"],
                rgb=item["rgb"],
                lab=item["lab"],
                hex_code=item["hex_code"],
                percent=item["percent"],
                mapped_color_id=mapped_color_id,
                color_family=family,
            )
        )

    return standardized


# ============================================================
# Database
# ============================================================

def fetch_color_reference(conn: PGConnection) -> list[dict[str, Any]]:
    """
    Load canonical colors from colors table.

    Expected schema example:
        colors(
            color_id BIGSERIAL PRIMARY KEY,
            color_name TEXT,
            color_family TEXT,
            lab_l REAL,
            lab_a REAL,
            lab_b REAL
        )
    """
    sql = """
        SELECT color_id, color_name, color_family, lab_l, lab_a, lab_b
        FROM colors
        WHERE lab_l IS NOT NULL
          AND lab_a IS NOT NULL
          AND lab_b IS NOT NULL
    """

    with conn.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return [
        {
            "color_id": row[0],
            "color_name": row[1],
            "color_family": row[2],
            "lab_l": row[3],
            "lab_a": row[4],
            "lab_b": row[5],
        }
        for row in rows
    ]


# April 15 - add function to insert garment

def insert_garment(
    conn: PGConnection,
    look_id: str,
    run_id: str,
    det: DetectionResult,
    model_id: int | None = None,
    mask_s3_uri: str | None = None,
) -> None:
    """
    Insert one detected garment into the garments table.

    Expected garments table columns:
        garment_id
        look_id
        run_id
        model_id
        category
        confidence
        bbox_x1
        bbox_y1
        bbox_x2
        bbox_y2
        mask_s3_uri
    """
    sql = """
        INSERT INTO garments (
            garment_id,
            look_id,
            run_id,
            model_id,
            category,
            confidence,
            bbox_x1,
            bbox_y1,
            bbox_x2,
            bbox_y2,
            mask_s3_uri
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    x1, y1, x2, y2 = det.bbox

    with conn.cursor() as cursor:
        cursor.execute(
            sql,
            (
                det.garment_id,
                look_id,
                run_id,
                model_id,
                det.category,
                det.confidence,
                x1,
                y1,
                x2,
                y2,
                mask_s3_uri,
            ),
        )




def insert_garment_colors(
    conn: PGConnection,
    garment_id: str,
    colors: Iterable[DominantColor],
) -> None:
    """
    Insert dominant colors into garment_colors table.
    """
    sql = """
        INSERT INTO garment_colors (
            garment_id,
            rank,
            hex,
            rgb_r,
            rgb_g,
            rgb_b,
            lab_l,
            lab_a,
            lab_b,
            percent,
            color_family,
            mapped_color_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    with conn.cursor() as cursor:
        for color in colors:
            cursor.execute(
                sql,
                (
                    garment_id,
                    color.rank,
                    color.hex_code,
                    color.rgb[0],
                    color.rgb[1],
                    color.rgb[2],
                    color.lab[0],
                    color.lab[1],
                    color.lab[2],
                    color.percent,
                    color.color_family,
                    color.mapped_color_id,
                ),
            )

    conn.commit()


# ============================================================
# Main Pipeline Logic
# ============================================================

def process_single_image(
    image_path: str,
    conn: PGConnection,
    n_colors: int = DEFAULT_K_COLORS,
) -> list[dict[str, Any]]:
    """
    Process one runway image through the full CV color pipeline.

    Returns a lightweight summary for logging/debugging.
    """
    image_rgb = load_image(image_path)
    detections = detect_garments_pytorch(image_rgb)

    print("Image shape:", image_rgb.shape)
    print("Number of detections:", len(detections))


    color_reference = fetch_color_reference(conn)

    summaries: list[dict[str, Any]] = []

    for det in detections:
        try:

            """ April 15 @ 8:30 am adding this function, but needs to confirm if correct"""
            # ------------------ START OF CODE BLOCK FOR REVIEW ---------------------------

            insert_garment(
                conn=conn,
                look_id=look_id,
                run_id=run_id,
                det=det,
                model_id=model_id,
                mask_s3_uri=None
            )

            # ------------------ END OF CODE BLOCK FOR REVIEW ------------------------------

            rgb_pixels = extract_masked_pixels(image_rgb, det.mask)
            raw_colors = cluster_dominant_colors(rgb_pixels, n_colors=n_colors)
            standardized = standardize_colors(raw_colors, color_reference)

            insert_garment_colors(conn, det.garment_id, standardized)

            summaries.append(
                {
                    "garment_id": det.garment_id,
                    "category": det.category,
                    "confidence": det.confidence,
                    "num_colors": len(standardized),
                    "status": "success",
                }
            )

        except Exception as exc:
            summaries.append(
                {
                    "garment_id": det.garment_id,
                    "category": det.category,
                    "confidence": det.confidence,
                    "num_colors": 0,
                    "status": f"failed: {exc}",
                }
            )

    return summaries


# ============================================================
# Example Entrypoint
# ============================================================

# def get_db_connection() -> PGConnection:
#     """
#     Replace these values with your real database connection settings.
#     """
#     return psycopg2.connect(
#         host="localhost",
#         dbname="fashion_db",
#         user="your_user",
#         password="your_password",
#         port=5432,
#     )


def run_cv(run_id, config):

    cv_run_id = run_id
    cv_config = config

    conn = psycopg2.connect(
        host = cv_config.db_host,
        database = cv_config.db_name,
        user = cv_config.db_user,
        password = cv_config.db_password,
        port = cv_config.db_port,
        sslmode = "require"
        )


    """
    Example public entrypoint for your CV pipeline.
    """

    try:

        print(f"Running Computer Vision with run_id={cv_run_id}")


        image_path = "/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/VogueImages/00001-chanel-spring-2026-ready-to-wear-credit-gorunway.webp"

        results = process_single_image(image_path, conn, n_colors=3)
        for row in results:
            print(row)

    except Exception as exc:
        conn.rollback()
        print(f"CV pipeline failed: {exc}")
        raise

    finally:
        conn.close()


# if __name__ == "__main__":
#     # Example:
#     # python cv_pipeline.py
#     #sample_image_path = "sample_runway.jpg"

#     sample_image_path = "/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/VogueImages/00001-chanel-spring-2026-ready-to-wear-credit-gorunway.webp"
#     run_cv(sample_image_path, config)


# RECOMMENDATION
#A stronger next step is to replace `detect_garments_pytorch()` with your actual PyTorch segmentation model so the masks are real instead of full-image placeholders.
