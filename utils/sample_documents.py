"""
Utility for generating sample documents for testing.
"""

def create_sample_requirements_document() -> str:
    """Create a comprehensive sample requirements document."""
    return """
# E-Commerce Platform Security Requirements

## Project Overview
This document outlines the security requirements for a cloud-based e-commerce platform that serves customers, administrators, and integrates with third-party payment processors.

## Stakeholders and External Entities
- **Customers**: End users who browse products, create accounts, and make purchases
- **Site Administrators**: Internal staff managing products, orders, and system configuration  
- **Payment Processor**: External service (Stripe) handling payment transactions
- **Shipping Provider**: Third-party logistics provider (FedEx) for order fulfillment
- **External Auditor**: Compliance auditor reviewing transaction logs and security controls

## System Architecture Components

### Presentation Layer
- **Web Application**: React-based frontend serving customer-facing e-commerce interface
- **Admin Portal**: Administrative dashboard for managing products, orders, and users
- **Mobile App**: iOS/Android application providing mobile shopping experience

### Application Layer  
- **Web Server**: Nginx reverse proxy handling HTTPS traffic and load balancing
- **Application Server**: Node.js/Express server hosting main business logic
- **Authentication Service**: Dedicated OAuth 2.0 service managing user sessions and JWT tokens
- **API Gateway**: Kong gateway providing rate limiting, authentication, and API management

### Business Logic Layer
- **Order Management Service**: Handles order creation, validation, status updates, and fulfillment
- **Inventory Service**: Manages product catalog, availability, and stock level tracking
- **Payment Gateway**: Internal service coordinating with external payment processors
- **User Management Service**: Handles user registration, profiles, and preference management
- **Notification Service**: Sends transactional emails and SMS notifications

### Data Layer
- **Customer Database**: PostgreSQL database storing user profiles, authentication data, and preferences
- **Product Database**: MySQL database containing product catalog, pricing, and inventory data
- **Order Database**: PostgreSQL database storing order history, transactions, and payment records
- **Analytics Database**: MongoDB storing user behavior data and business intelligence metrics
- **Session Store**: Redis cache managing user sessions and temporary data
- **File Storage**: AWS S3 bucket storing product images, documents, and static assets

### Infrastructure and Security
- **Load Balancer**: AWS Application Load Balancer distributing traffic across multiple servers
- **Web Application Firewall**: CloudFlare WAF protecting against common web attacks
- **CDN**: CloudFlare CDN for global content delivery and DDoS protection
- **Monitoring Service**: DataDog providing system monitoring, alerting, and log aggregation

## Data Flow Requirements

### Customer Purchase Flow
1. Customer accesses website through CDN and WAF protection via HTTPS
2. Load balancer routes traffic to available web servers
3. Web server authenticates user through OAuth service using JWT tokens
4. Customer browses products served from CDN-cached product database queries
5. Order management service validates cart items and checks inventory availability
6. Payment gateway encrypts and transmits payment data to Stripe processor
7. Order database stores transaction with PCI-compliant data handling
8. Notification service sends order confirmation via encrypted email
9. Shipping service receives order details through secure API integration

### Administrative Operations Flow
1. Administrator connects to admin portal through corporate VPN
2. Multi-factor authentication validates admin credentials through OAuth service
3. Admin portal communicates with business services through internal API gateway
4. Product updates flow from admin interface to product database
5. Order management actions are logged to audit trail with administrator attribution
6. System configuration changes require additional approval workflows

### Payment Processing Flow
1. Customer payment details collected through PCI-compliant frontend forms
2. Payment gateway tokenizes sensitive data before transmission
3. Encrypted payment data sent to Stripe via TLS 1.3 secured connection
4. Payment processor returns transaction status and confirmation tokens
5. Order database stores transaction reference without storing card details
6. Financial reconciliation data synchronized with internal accounting systems

## Security Requirements

### Data Classification and Handling
- **PCI Data**: Credit card numbers, CVV codes - encrypted at rest and in transit
- **PII Data**: Customer names, addresses, email - encrypted storage with access controls
- **Internal Confidential**: Business metrics, pricing strategies - internal access only
- **Public Data**: Product descriptions, marketing content - unrestricted access

### Authentication and Authorization Requirements
- All customer-facing interfaces require HTTPS with TLS 1.3 minimum
- Customer authentication uses email/password with optional two-factor authentication
- Administrative access requires multi-factor authentication with smart card or authenticator app
- Service-to-service communication uses mutual TLS certificates
- API access controlled through OAuth 2.0 with granular scope permissions
- Session tokens have configurable expiration with sliding window renewal

### Trust Boundaries and Network Security
- **Internet to DMZ**: Customer traffic filtered through WAF and DDoS protection
- **DMZ to Application**: Web servers isolated in application security group
- **Application to Data**: Database access through encrypted connections only
- **Internal to External**: Payment processor connections through dedicated VPN
- **Management Network**: Administrative access through separate VPN tunnel

### Compliance and Audit Requirements
- PCI DSS Level 1 compliance for payment card processing
- SOX compliance for financial reporting and transaction audit trails
- GDPR compliance for European customer data protection and privacy
- Regular penetration testing and vulnerability assessments
- Comprehensive audit logging for all administrative and financial transactions

## Risk Assessment
This system processes high-value financial transactions and stores sensitive customer data, making it an attractive target for cybercriminals. The internet-facing architecture increases attack surface, while third-party integrations introduce supply chain risks. Regulatory compliance failures could result in significant financial penalties and reputational damage.

## Implementation Priorities
1. Implement comprehensive input validation and output encoding
2. Deploy Web Application Firewall with custom rule sets
3. Enable comprehensive audit logging and monitoring
4. Implement database encryption at rest and in transit
5. Deploy intrusion detection and prevention systems
6. Establish incident response and business continuity procedures
    """.strip()