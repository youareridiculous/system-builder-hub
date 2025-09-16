"""
SSM Parameter Store loader for secrets
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_ssm_parameters_if_configured():
    """Load parameters from SSM Parameter Store if configured"""
    env = os.environ.get('ENV', 'development')
    ssm_path = os.environ.get('SSM_PATH')
    
    # Only load from SSM in staging/production
    if env not in ['staging', 'production'] or not ssm_path:
        return
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        # Create SSM client
        ssm = boto3.client('ssm')
        
        # Get parameters by path
        try:
            response = ssm.get_parameters_by_path(
                Path=ssm_path,
                Recursive=True,
                WithDecryption=True
            )
            
            # Inject parameters into environment
            for param in response['Parameters']:
                param_name = param['Name'].split('/')[-1]  # Get just the parameter name
                param_value = param['Value']
                
                # Only set if not already in environment
                if param_name not in os.environ:
                    os.environ[param_name] = param_value
                    logger.info(f"Loaded SSM parameter: {param_name}")
                else:
                    logger.debug(f"SSM parameter {param_name} already in environment")
            
            logger.info(f"Loaded {len(response['Parameters'])} parameters from SSM path: {ssm_path}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                logger.warning("Access denied to SSM Parameter Store - check IAM permissions")
            else:
                logger.error(f"SSM error: {e}")
        except NoCredentialsError:
            logger.warning("No AWS credentials found - SSM parameters not loaded")
            
    except ImportError:
        logger.warning("boto3 not available - SSM parameters not loaded")
    except Exception as e:
        logger.error(f"Failed to load SSM parameters: {e}")

def get_ssm_parameter(parameter_name: str, default: str = None) -> str:
    """Get a single parameter from SSM"""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        ssm = boto3.client('ssm')
        
        try:
            response = ssm.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            return response['Parameter']['Value']
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                logger.warning(f"SSM parameter not found: {parameter_name}")
                return default
            else:
                logger.error(f"SSM error getting parameter {parameter_name}: {e}")
                return default
        except NoCredentialsError:
            logger.warning("No AWS credentials found")
            return default
            
    except ImportError:
        logger.warning("boto3 not available")
        return default
    except Exception as e:
        logger.error(f"Failed to get SSM parameter {parameter_name}: {e}")
        return default
