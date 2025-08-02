"""
Service for fetching external threat intelligence data.
"""
import aiohttp
import logging
from typing import Set
from config.settings import Config

logger = logging.getLogger(__name__)

class ExternalDataService:
    """Manages external API calls for threat intelligence."""
    
    def __init__(self, config: dict):
        self.config = config
    
    async def fetch_cisa_kev_catalog(self) -> Set[str]:
        """Fetch CISA KEV catalog with basic async handling."""
        try:
            logger.info("Fetching CISA KEV catalog...")
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.get('api_timeout', 30))
            ) as session:
                async with session.get(self.config['cisa_kev_url']) as response:
                    if response.status == 200:
                        data = await response.json()
                        kev_set = {vuln['cveID'] for vuln in data.get('vulnerabilities', [])}
                        logger.info(f"Successfully loaded {len(kev_set)} entries from CISA KEV catalog")
                        return kev_set
                    else:
                        logger.warning(f"Failed to fetch CISA KEV catalog: HTTP {response.status}")
                        return set()
                        
        except Exception as e:
            logger.warning(f"Failed to fetch CISA KEV catalog: {e}")
            return set()
    
    def check_cve_relevance(self, cve_id: str, kev_catalog: Set[str]) -> bool:
        """Check if a CVE is relevant based on age and exploitation status."""
        # Always consider KEV CVEs as relevant
        if cve_id in kev_catalog:
            logger.debug(f"CVE {cve_id} is in CISA KEV catalog - relevant")
            return True
        
        try:
            # Extract year from CVE ID format: CVE-YYYY-NNNNN
            parts = cve_id.split('-')
            if len(parts) >= 2:
                year = int(parts[1])
                from datetime import datetime
                cutoff_year = datetime.now().year - self.config['cve_relevance_years']
                
                if year >= cutoff_year:
                    return True
                else:
                    logger.debug(f"CVE {cve_id} ({year}) is older than {self.config['cve_relevance_years']} years")
                    return False
        except (ValueError, IndexError):
            logger.warning(f"Could not parse year from CVE ID {cve_id}")
            return True
        
        return False