"""
Health Check Stage
"""

from typing import Dict, Any
import os
import aiohttp
import asyncio
from marketpilot.data_farm.stages.base_stage import BaseStage
from marketpilot.utils.logger import log_event


class HealthCheckStage(BaseStage):
    """
    Purpose: Verify APIs are available BEFORE starting data collection
    Runs: ONCE at pipeline start
    """

    def __init__(self):
        super().__init__("health_check")

    async def _process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Health check based on active adapters in config
        """
        # Results container
        health_results = {
            "apis_checked": 0,
            "apis_healthy": 0,
            "api_details": [],
            "overall_status": "unknown"
        }
        
        # ============================================
        # Step 1: Build API list from ACTIVE adapters
        # ============================================
        adapters = data.get("adapters", [])
        if not adapters:
            log_event(
                stage=self.stage_name,
                block="health_check",
                level="ERROR",
                msg="No adapters loaded",
            )
            health_results["overall_status"] = "critical"
            data["health_check"] = health_results
            return data
        
        # Extract unique adapter types from active adapters
        active_types = set()
        for adapter in adapters:
            adapter_type = adapter.config.get("type")
            if adapter_type:
                active_types.add(adapter_type)
        
        # Map adapter types to health URLs
        type_to_health_url = {
            "price": os.getenv("PRICE_API_HEALTH_URL"),
            "news": os.getenv("NEWS_API_HEALTH_URL"),
            "fundamental": os.getenv("FUNDAMENTAL_API_HEALTH_URL"),
        }
        
        # Build list of APIs to check (only active adapters)
        apis_to_check = []
        for adapter_type in active_types:
            health_url = type_to_health_url.get(adapter_type)
            if health_url:
                apis_to_check.append((adapter_type, health_url))
            else:
                log_event(
                    stage=self.stage_name,
                    block="health_check",
                    level="WARNING",
                    msg=f"No health URL configured for {adapter_type}",
                )
        
        if not apis_to_check:
            log_event(
                stage=self.stage_name,
                block="health_check",
                level="ERROR",
                msg="No health endpoints configured for active adapters",
            )
            health_results["overall_status"] = "critical"
            data["health_check"] = health_results
            return data
        
        # ============================================
        # Step 2: Check Each API Health
        # ============================================
        for api_type, health_url in apis_to_check:
            health_results["apis_checked"] += 1
            
            is_healthy = await self._check_api(api_type, health_url)
            
            if is_healthy:
                health_results["apis_healthy"] += 1
                health_results["api_details"].append({
                    "type": api_type,
                    "status": "healthy"
                })
            else:
                health_results["api_details"].append({
                    "type": api_type,
                    "status": "unhealthy"
                })
        
        # ============================================
        # Step 3: Validate Config
        # ============================================
        config = data.get("config", {})
        config_valid = self._validate_config(config)
        
        if not config_valid:
            health_results["overall_status"] = "critical"
            data["health_check"] = health_results
            return data
        
        # ============================================
        # Step 4: Determine Overall Status
        # ============================================
        if health_results["apis_healthy"] == 0:
            health_results["overall_status"] = "critical"
        elif health_results["apis_healthy"] == health_results["apis_checked"]:
            health_results["overall_status"] = "healthy"
        else:
            health_results["overall_status"] = "degraded"
        
        # Log result
        log_event(
            stage=self.stage_name,
            block="health_check",
            level="INFO" if health_results["overall_status"] == "healthy" else "WARNING",
            msg=f"Health check complete: {health_results['overall_status']}",
            extra={
                "healthy_apis": health_results["apis_healthy"],
                "total_apis": health_results["apis_checked"],
                "checked_types": [t for t, _ in apis_to_check],
            },
        )
        
        data["health_check"] = health_results
        return data

    async def _check_api(self, api_type: str, health_url: str) -> bool:
        """Check if API health endpoint returns success"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    
                    if response.status != 200:
                        log_event(
                            stage=self.stage_name,
                            block="api_health",
                            level="ERROR",
                            msg=f"{api_type.upper()} API returned HTTP {response.status}",
                        )
                        return False
                    
                    health_data = await response.json()
                    success = health_data.get("success", False)
                    
                    if success:
                        log_event(
                            stage=self.stage_name,
                            block="api_health",
                            level="INFO",
                            msg=f"{api_type.upper()} API is healthy",
                            extra={
                                "api_type": api_type,
                                "version": health_data.get("version"),
                            },
                        )
                        return True
                    else:
                        log_event(
                            stage=self.stage_name,
                            block="api_health",
                            level="WARNING",
                            msg=f"{api_type.upper()} API returned success=false",
                        )
                        return False
        
        except asyncio.TimeoutError:
            log_event(
                stage=self.stage_name,
                block="api_health",
                level="ERROR",
                msg=f"{api_type.upper()} API timeout",
            )
            return False
        
        except Exception as e:
            log_event(
                stage=self.stage_name,
                block="api_health",
                level="ERROR",
                msg=f"{api_type.upper()} API error: {str(e)}",
            )
            return False

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Simple config validation"""
        required = ["adapters", "output", "quality"]
        
        for key in required:
            if key not in config:
                log_event(
                    stage=self.stage_name,
                    block="config",
                    level="ERROR",
                    msg=f"Missing config key: {key}",
                )
                return False
        
        return True