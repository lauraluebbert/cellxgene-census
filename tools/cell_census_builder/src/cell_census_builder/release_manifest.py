"""
Tools to manage the release.json manifest file.
"""
import json
from typing import Dict, Optional, Union, cast

import s3fs
from typing_extensions import TypedDict

from .util import urlcat

"""
The release.json schema is a semi-public format, used by all end-user packages.
"""

CensusVersionName = str  # census version name, e.g., "release-99", "2022-10-01-test", etc.
CensusLocator = TypedDict(
    "CensusLocator",
    {
        "uri": str,  # resource URI
        "s3_region": Optional[str],  # if an S3 URI, has optional region
    },
)
CensusVersionDescription = TypedDict(
    "CensusVersionDescription",
    {
        "release_date": Optional[str],  # date of release, optional
        "release_build": str,  # date of build
        "soma": CensusLocator,  # SOMA objects locator
        "h5ads": CensusLocator,  # source H5ADs locator
    },
)
CensusReleaseManifest = Dict[CensusVersionName, Union[CensusVersionName, CensusVersionDescription]]

CELL_CENSUS_REGION = "us-west-2"
CELL_CENSUS_RELEASE_FILE = "release.json"

# The following tags MUST be in any "valid" Census release.json.  This list may grow.
REQUIRED_TAGS = [
    "latest",  # default census - used by the Python/R packages
]


def get_release_manifest(census_base_url: str, s3_anon: bool = False) -> CensusReleaseManifest:
    """
    Fetch the census release manifest.

    Args:
        census_base_url:
            The base S3 URL of the Census.

    Returns:
        A `CensusReleaseManifest` containing the current release manifest.
    """
    s3 = s3fs.S3FileSystem(anon=s3_anon)
    with s3.open(urlcat(census_base_url, CELL_CENSUS_RELEASE_FILE)) as f:
        return cast(CensusReleaseManifest, json.loads(f.read()))


def commit_release_manifest(census_base_url: str, release_manifest: CensusReleaseManifest) -> None:
    """
    Write a new release manifest to the Census.
    """
    # Out of an abundance of caution, validate the contents
    validate_release_manifest(census_base_url, release_manifest)
    _overwrite_release_manifest(census_base_url, release_manifest)


def _overwrite_release_manifest(census_base_url: str, release_manifest: CensusReleaseManifest) -> None:
    # This is a stand-alone function for ease of testing/mocking.
    s3 = s3fs.S3FileSystem(anon=False)
    with s3.open(urlcat(census_base_url, CELL_CENSUS_RELEASE_FILE), mode="w") as f:
        f.write(json.dumps(release_manifest))


def validate_release_manifest(
    census_base_url: str, release_manifest: CensusReleaseManifest, live_corpus_check: bool = True, s3_anon: bool = False
) -> None:
    if not isinstance(release_manifest, dict):
        raise TypeError("Release manifest must be a dictionary")

    if len(release_manifest) == 0:
        raise ValueError("Release manifest is empty")

    for rls_tag, rls_info in release_manifest.items():
        if not isinstance(rls_tag, str):
            raise TypeError("Release tags must be a string")

        if isinstance(rls_info, str):
            # alias
            if rls_info not in release_manifest:
                raise ValueError(f"Release manifest contains undefined tag reference {rls_info}")
        else:
            # record
            _validate_release_info(rls_tag, rls_info, census_base_url)
            if live_corpus_check:
                _validate_exists(rls_info, s3_anon)

    for rls_tag in REQUIRED_TAGS:
        if rls_tag not in release_manifest:
            raise ValueError(f"Release manifest is missing required release tag: {rls_tag}")


def _validate_release_info(
    rls_tag: CensusVersionName, rls_info: CensusVersionDescription, census_base_url: str
) -> None:
    if not isinstance(rls_info, dict):
        raise TypeError("Release records must be a dict")

    if not all(k in rls_info for k in ("release_build", "soma", "h5ads")):
        raise ValueError("Release info is missing required field")

    if rls_info["release_build"] != rls_tag:
        raise ValueError("release_build must be the same as the release tag")

    if rls_info["soma"] != {"uri": urlcat(census_base_url, rls_tag, "soma/"), "s3_region": CELL_CENSUS_REGION}:
        raise ValueError(f"Release record for {rls_tag} contained unexpected SOMA locator")
    if rls_info["h5ads"] != {"uri": urlcat(census_base_url, rls_tag, "h5ads/"), "s3_region": CELL_CENSUS_REGION}:
        raise ValueError(f"Release record for {rls_tag} contained unexpected H5AD locator")


def _validate_exists(rls_info: CensusVersionDescription, s3_anon: bool) -> None:
    s3 = s3fs.S3FileSystem(anon=s3_anon)

    uri = rls_info["soma"]["uri"]
    if not s3.isdir(uri):
        raise ValueError(f"SOMA URL in release.json does not exist {uri}")
    uri = rls_info["h5ads"]["uri"]
    if not s3.isdir(uri):
        raise ValueError(f"H5ADS URL in release.json does not exist {uri}")
