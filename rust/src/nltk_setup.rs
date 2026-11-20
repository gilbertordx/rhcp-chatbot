//! Downloads the one NLTK data package this app needs.
//! Python equivalent: `app/scripts/setup_nltk.py` (which fetched four packages;
//! only the Punkt sentence model is used by the Rust version).

use std::fs;
use std::io::{Cursor, Read};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};

use crate::nlp::punkt::{find_punkt_dir, nltk_data_dirs};

const PUNKT_URL: &str = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt_tab.zip";

pub fn run() -> Result<()> {
    println!("--- Starting NLTK data setup ---");
    println!("Checking for NLTK package: punkt_tab...");
    if let Some(dir) = find_punkt_dir() {
        println!("Package 'punkt_tab' already installed ({}).", dir.display());
        println!("--- NLTK data setup complete ---");
        return Ok(());
    }
    println!("Package 'punkt_tab' not found. Downloading...");
    let target: PathBuf = nltk_data_dirs()
        .into_iter()
        .next()
        .context("no NLTK data directory to install into")?;
    let bytes = reqwest::blocking::get(PUNKT_URL)
        .and_then(|r| r.error_for_status())
        .and_then(|r| r.bytes())
        .with_context(|| format!("downloading {PUNKT_URL}"))?;
    extract_punkt(&bytes, &target.join("tokenizers"))?;
    println!("Package 'punkt_tab' downloaded successfully.");
    println!("--- NLTK data setup complete ---");
    Ok(())
}

/// Unpack the zip under `dest`. Entry paths are checked so nothing can escape `dest`.
fn extract_punkt(zip_bytes: &[u8], dest: &Path) -> Result<()> {
    let mut archive = zip::ZipArchive::new(Cursor::new(zip_bytes)).context("reading the downloaded zip")?;
    let mut written = 0;
    for i in 0..archive.len() {
        let mut entry = archive.by_index(i)?;
        let Some(relative) = entry.enclosed_name() else {
            bail!("unsafe path in zip: {:?}", entry.name())
        };
        let out = dest.join(relative);
        if entry.is_dir() {
            fs::create_dir_all(&out)?;
            continue;
        }
        if let Some(parent) = out.parent() {
            fs::create_dir_all(parent)?;
        }
        let mut data = Vec::new();
        entry.read_to_end(&mut data)?;
        fs::write(&out, data)?;
        written += 1;
    }
    if written == 0 {
        bail!("the downloaded zip was empty");
    }
    Ok(())
}
