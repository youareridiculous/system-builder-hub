#!/bin/bash
set -euo pipefail

# Deployment Verification Script for SBH
# Verifies deployment health via ALB and domain

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOST="${HOST:-sbh.umbervale.com}"
ALB_DNS="${ALB_DNS:-}"
MAX_RETRIES="${MAX_RETRIES:-10}"
RETRY_DELAY="${RETRY_DELAY:-10}"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Check required tools
check_dependencies() {
    local missing_deps=()
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

# Test HTTP endpoint with retries
test_endpoint() {
    local url="$1"
    local description="$2"
    local expected_status="${3:-200}"
    
    log "Testing $description: $url"
    
    local retry_count=0
    local response_code
    local response_body
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        if response_body=$(curl -fsS -w "%{http_code}" -o /tmp/response_body.json "$url" 2>/dev/null); then
            response_code="${response_body: -3}"
            
            if [ "$response_code" = "$expected_status" ]; then
                success "✓ $description responded with $response_code"
                
                # Pretty print JSON response if it's valid JSON
                if jq . /tmp/response_body.json &> /dev/null; then
                    echo ""
                    info "Response body:"
                    jq . /tmp/response_body.json
                    echo ""
                else
                    info "Response body:"
                    cat /tmp/response_body.json
                    echo ""
                fi
                
                rm -f /tmp/response_body.json
                return 0
            else
                warn "✗ $description responded with $response_code (expected $expected_status)"
            fi
        else
            warn "✗ $description failed to respond (attempt $((retry_count + 1))/$MAX_RETRIES)"
        fi
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $MAX_RETRIES ]; then
            log "Retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
        fi
    done
    
    error "✗ $description failed after $MAX_RETRIES attempts"
    rm -f /tmp/response_body.json
    return 1
}

# Test HTTPS endpoint
test_https_endpoint() {
    local url="https://$HOST/api/health"
    test_endpoint "$url" "HTTPS Health Check" "200"
}

# Test HTTP endpoint (should redirect to HTTPS)
test_http_endpoint() {
    local url="http://$HOST/api/health"
    test_endpoint "$url" "HTTP Health Check (should redirect)" "301"
}

# Test ALB endpoint directly
test_alb_endpoint() {
    if [ -n "$ALB_DNS" ]; then
        local url="http://$ALB_DNS/api/health"
        test_endpoint "$url" "ALB Direct Health Check" "200"
    else
        warn "ALB_DNS not provided, skipping ALB direct test"
    fi
}

# Test domain resolution
test_domain_resolution() {
    log "Testing domain resolution for: $HOST"
    
    if nslookup "$HOST" &> /dev/null; then
        success "✓ Domain $HOST resolves"
        
        # Show the resolved IP
        local resolved_ip
        resolved_ip=$(nslookup "$HOST" | grep -A 1 "Name:" | tail -1 | awk '{print $2}')
        if [ -n "$resolved_ip" ]; then
            info "Resolved to: $resolved_ip"
        fi
    else
        error "✗ Domain $HOST does not resolve"
        return 1
    fi
}

# Test SSL certificate
test_ssl_certificate() {
    log "Testing SSL certificate for: $HOST"
    
    if echo | openssl s_client -servername "$HOST" -connect "$HOST:443" 2>/dev/null | openssl x509 -noout -dates &> /dev/null; then
        success "✓ SSL certificate is valid"
        
        # Show certificate details
        local cert_info
        cert_info=$(echo | openssl s_client -servername "$HOST" -connect "$HOST:443" 2>/dev/null | openssl x509 -noout -subject -dates)
        info "Certificate details:"
        echo "$cert_info" | sed 's/^/  /'
    else
        warn "✗ SSL certificate test failed (this is expected if HTTPS is not yet configured)"
    fi
}

# Main execution
main() {
    log "Starting deployment verification..."
    log "Configuration:"
    log "  Host: $HOST"
    log "  ALB DNS: ${ALB_DNS:-'not provided'}"
    log "  Max Retries: $MAX_RETRIES"
    log "  Retry Delay: $RETRY_DELAY seconds"
    echo ""
    
    check_dependencies
    
    local failed_tests=0
    
    # Test domain resolution
    if ! test_domain_resolution; then
        failed_tests=$((failed_tests + 1))
    fi
    echo ""
    
    # Test SSL certificate (optional)
    test_ssl_certificate
    echo ""
    
    # Test HTTPS endpoint
    if ! test_https_endpoint; then
        failed_tests=$((failed_tests + 1))
    fi
    echo ""
    
    # Test HTTP endpoint (should redirect)
    if ! test_http_endpoint; then
        failed_tests=$((failed_tests + 1))
    fi
    echo ""
    
    # Test ALB endpoint directly
    test_alb_endpoint
    echo ""
    
    # Summary
    if [ $failed_tests -eq 0 ]; then
        success "🎉 All verification tests passed!"
        success "Deployment is healthy and accessible"
        echo ""
        info "You can access SBH at:"
        info "  HTTPS: https://$HOST"
        info "  Health: https://$HOST/api/health"
        if [ -n "$ALB_DNS" ]; then
            info "  ALB Direct: http://$ALB_DNS"
        fi
    else
        error "❌ $failed_tests verification test(s) failed"
        error "Please check the deployment and try again"
        exit 1
    fi
}

# Run main function
main "$@"
