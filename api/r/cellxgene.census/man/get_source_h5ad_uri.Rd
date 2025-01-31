% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/source_h5ad.R
\name{get_source_h5ad_uri}
\alias{get_source_h5ad_uri}
\title{Locate source h5ad file for a dataset.}
\usage{
get_source_h5ad_uri(dataset_id, census_version = "latest")
}
\arguments{
\item{dataset_id}{The dataset_id of interest.}

\item{census_version}{The census version.}
}
\value{
A list with \code{uri} and optional \code{s3_region}.
}
\description{
Locate source h5ad file for a dataset.
}
