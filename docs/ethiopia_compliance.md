## ፋይል #304: `docs/ethiopia_compliance.md`

```markdown
# Wolloyewa Store Bot - Ethiopia Compliance Guide

## 📋 Overview

| Attribute | Value |
|-----------|-------|
| Document Version | 1.0 |
| Effective Date | 2024-01-15 |
| Regulatory Body | Ministry of Trade, Ministry of Revenue |
| Applicable Laws | VAT Proclamation, E-commerce Directive |

---

## 🏛️ Regulatory Framework

### Key Legislation

| Law | Number | Purpose | Impact |
|-----|--------|---------|--------|
| VAT Proclamation | No. 285/2002 | Value Added Tax | 15% VAT on goods |
| Income Tax Proclamation | No. 979/2016 | Withholding tax | 2% on payments |
| E-commerce Directive | No. 123/2019 | Online business rules | Registration required |
| Data Protection Law | Proclamation 1321/2024 | Privacy & security | PII handling rules |
| Consumer Protection | No. 813/2013 | Buyer rights | Return/refund policies |

### Regulatory Bodies

| Authority | Responsibility | Contact |
|-----------|----------------|---------|
| Ministry of Trade | Business licensing | trade.gov.et |
| Ministry of Revenue | Tax collection | mofed.gov.et |
| Ethiopian Communications Authority | Tech compliance | eca.gov.et |
| National Bank of Ethiopia | Payment systems | nbe.gov.et |

---

## 💰 Tax Compliance

### VAT (Value Added Tax)

```python
# Tax calculation implementation
VAT_RATE = Decimal('0.15')  # 15%

def calculate_vat(amount: Decimal) -> Decimal:
    """Calculate VAT for taxable goods"""
    return amount * VAT_RATE

# VAT registration threshold
VAT_THRESHOLD = Decimal('1_000_000')  # 1 million ETB annually
```

#### VAT Rates by Product Category

| Category | VAT Rate | Notes |
|----------|----------|-------|
| Electronics | 15% | Standard rate |
| Clothing | 15% | Standard rate |
| Food | 15% | Standard rate |
| Books | 0% | Exempt |
| Medicine | 0% | Exempt |
| Agricultural products | 0% | Exempt |
| Exports | 0% | Zero-rated |

### Withholding Tax

```python
WITHHOLDING_RATE = Decimal('0.02')  # 2%

def calculate_withholding(amount: Decimal) -> Decimal:
    """Calculate withholding tax for vendor payments"""
    return amount * WITHHOLDING_RATE
```

### Turnover Tax

```python
TURNOVER_RATE = Decimal('0.02')  # 2%
TURNOVER_THRESHOLD = Decimal('1_000_000')

def calculate_turnover_tax(amount: Decimal, annual_revenue: Decimal) -> Decimal:
    """Calculate turnover tax for non-VAT registered businesses"""
    if annual_revenue < TURNOVER_THRESHOLD:
        return amount * TURNOVER_RATE
    return Decimal('0')
```

### Tax Reporting Schedule

| Report Type | Frequency | Due Date | Penalty for Late |
|-------------|-----------|----------|------------------|
| VAT Return | Monthly | 20th of next month | 5% + interest |
| Withholding Tax | Monthly | 20th of next month | 5% + interest |
| Annual Income | Yearly | June 30 | 10% + interest |
| Turnover Tax | Quarterly | 30 days after quarter | 5% + interest |

---

## 📄 Legal Invoice Requirements

### Mandatory Invoice Fields

| Field | Description | Status |
|-------|-------------|--------|
| Invoice number | Sequential, unique | ✅ |
| Issue date | Ethiopian calendar | ✅ |
| Seller TIN | 10-digit number | ✅ |
| Seller VAT number | If registered | ✅ |
| Buyer TIN | If applicable | ⚠️ |
| Buyer name and address | Complete address | ✅ |
| Description of goods | Detailed | ✅ |
| Quantity | Units | ✅ |
| Unit price | ETB | ✅ |
| Total amount | ETB | ✅ |
| VAT amount | 15% calculated | ✅ |
| Withholding tax | 2% calculated | ✅ |
| QR code | For verification | ✅ |

### Invoice Numbering Format

```python
# Standard format: INV-YYYYMM-XXXXXX
def generate_invoice_number(counter: int) -> str:
    year_month = datetime.now().strftime("%Y%m")
    return f"INV-{year_month}-{counter:06d}"
```

### Invoice Storage Requirements

| Requirement | Period | Format |
|-------------|--------|--------|
| Active invoices | 6 years | Original |
| Archived invoices | 10 years | Digital/Paper |
| Tax audit access | Immediate | Digital |

---

## 🏢 Business Registration

### Required Licenses

| License | Authority | Processing Time | Cost |
|---------|-----------|-----------------|------|
| Trade License | Ministry of Trade | 5-7 days | 500 ETB |
| TIN Certificate | Ministry of Revenue | 1-3 days | Free |
| VAT Registration | Ministry of Revenue | 3-5 days | Free |
| E-commerce Permit | Ministry of Trade | 7-14 days | 1000 ETB |

### Registration Process

```bash
# Step 1: Register business name
# Step 2: Obtain TIN
# Step 3: Apply for trade license
# Step 4: Register for VAT (if applicable)
# Step 5: Open business bank account
# Step 6: Register with social security
```

### Post-Registration Requirements

| Requirement | Frequency | Deadline |
|-------------|-----------|----------|
| Tax declaration | Monthly | 20th |
| License renewal | Annual | December 31 |
| Employee registration | Upon hiring | 15 days |
| Financial audit | Annual | June 30 |

---

## 🔒 Data Protection (Proclamation 1321/2024)

### Data Classification

| Level | Description | Examples | Protection |
|-------|-------------|----------|------------|
| Public | Available to all | Product listings | None |
| Internal | Employees only | Sales reports | Access control |
| Confidential | Limited access | Customer data | Encryption |
| Restricted | Strict control | Payment info | Full encryption |

### Data Localization Requirements

```python
# Data that must stay in Ethiopia
ETHIOPIAN_DATA_TYPES = {
    "PERSONAL": ["national_id", "passport", "drivers_license"],
    "FINANCIAL": ["bank_account", "payment_transactions"],
    "GOVERNMENT": ["tin", "business_license"],
    "HEALTH": ["medical_records", "health_insurance"]
}
```

### Consent Management

```python
class ConsentType:
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    THIRD_PARTY = "third_party"
    LOCATION = "location"

class ConsentStatus:
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
```

### Data Breach Notification

| Breach Type | Notification Time | Authority |
|-------------|-------------------|-----------|
| Personal data | 72 hours | Ministry of Innovation |
| Financial data | 24 hours | National Bank |
| Payment data | 1 hour | Payment processor |

---

## 💳 Payment Compliance

### Approved Payment Gateways

| Gateway | Approved By | Status | Integration |
|---------|-------------|--------|-------------|
| Chapa | National Bank | ✅ Active | ✅ Complete |
| Telebirr | Ethio Telecom | ✅ Active | ✅ Complete |
| CBE Birr | CBE | ✅ Active | ✅ Complete |

### Payment Transaction Records

```python
# Required fields for each transaction
payment_record = {
    "transaction_id": str,
    "amount": Decimal,
    "currency": "ETB",
    "payment_method": str,
    "timestamp": datetime,
    "merchant_id": str,
    "customer_id": str,  # Hashed
    "status": str,
    "reference": str
}
```

### Record Retention

| Transaction Type | Retention Period |
|------------------|------------------|
| Successful | 10 years |
| Failed | 5 years |
| Refunded | 10 years |
| Disputed | 15 years |

---

## 📦 Consumer Protection

### Return Policy Requirements

```python
RETURN_POLICY = {
    "return_window_days": 14,
    "refund_timeline_days": 7,
    "condition": "unused_original_packaging",
    "exceptions": ["perishable", "digital_goods", "personalized"]
}
```

### Mandatory Disclosures

| Information | Where | When |
|-------------|-------|------|
| Business name | Footer | Always |
| TIN number | Invoice | Every transaction |
| Terms of service | Registration | Before signup |
| Privacy policy | Registration | Before signup |
| Return policy | Checkout | Before payment |
| Delivery terms | Product page | Before purchase |

### Customer Rights

```markdown
## Customer Rights Summary

1. **Right to Information**: Full product details before purchase
2. **Right to Cancel**: 14-day cooling-off period
3. **Right to Return**: 14 days for defective products
4. **Right to Refund**: Full refund for undelivered orders
5. **Right to Complaint**: Access to dispute resolution
```

---

## 🌐 E-commerce Platform Compliance

### Platform Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Business registration | ✅ | Trade license |
| Tax registration | ✅ | TIN certificate |
| Terms of service | ✅ | Published |
| Privacy policy | ✅ | Published |
| Dispute resolution | ✅ | Support system |
| Complaint handling | ✅ | Ticket system |

### Seller Verification

```python
# Required seller documents
seller_requirements = {
    "individual": ["national_id", "tin"],
    "business": ["trade_license", "tin", "vat_certificate"],
    "foreign": ["investment_license", "business_registration"]
}
```

### Platform Responsibilities

| Responsibility | Implementation | Audit |
|----------------|----------------|-------|
| Data security | Encryption, access control | Quarterly |
| Payment protection | Escrow, fraud detection | Monthly |
| Dispute mediation | Support team | Continuous |
| Tax reporting | Automated calculations | Monthly |

---

## 📊 Reporting Requirements

### Tax Reports

```python
# Generate tax report
def generate_tax_report(start_date, end_date):
    return {
        "total_sales": total_amount,
        "vat_collected": vat_total,
        "withholding_collected": withholding_total,
        "turnover_tax": turnover_total,
        "transactions": transaction_count
    }
```

### Business Reports

| Report | Frequency | Recipient |
|--------|-----------|-----------|
| Sales summary | Monthly | Internal |
| Tax report | Monthly | Ministry of Revenue |
| Annual return | Yearly | Ministry of Trade |
| Audit report | Yearly | Internal |

---

## 🔍 Audit Preparation

### Documentation Required

| Document | Retention | Format |
|----------|-----------|--------|
| Sales records | 10 years | Digital |
| Purchase records | 10 years | Digital |
| Tax returns | 10 years | Digital/Paper |
| Bank statements | 10 years | Digital/Paper |
| Licenses | Active | Paper |
| Employee records | 7 years | Digital/Paper |

### Audit Checklist

- [ ] Business license current
- [ ] TIN certificate valid
- [ ] VAT registration (if applicable)
- [ ] Tax returns filed on time
- [ ] Invoices in correct format
- [ ] Data protection compliant
- [ ] Payment gateway approved
- [ ] Terms of service up-to-date
- [ ] Privacy policy published
- [ ] Return policy posted

---

## ⚠️ Penalties & Fines

| Violation | Fine | Legal Action |
|-----------|------|--------------|
| No business license | 10,000 - 50,000 ETB | Closure |
| Tax evasion | 100% of tax + interest | Imprisonment |
| No VAT registration | 50,000 ETB | Fine |
| Data breach (negligence) | 100,000 ETB | Lawsuit |
| False advertising | 20,000 ETB | Corrective action |

---

## 📞 Regulatory Contacts

| Authority | Phone | Email | Website |
|-----------|-------|-------|---------|
| Ministry of Trade | 8335 | info@motic.gov.et | motic.gov.et |
| Ministry of Revenue | 8015 | info@mor.gov.et | mor.gov.et |
| NBE Payment Systems | 011-517-7000 | payment@nbe.gov.et | nbe.gov.et |
| ECA | 011-557-1500 | info@eca.gov.et | eca.gov.et |

---

## 📚 Resources

### Official Documents
- [VAT Proclamation](https://www.mor.gov.et/proclamations)
- [E-commerce Directive](https://www.motic.gov.et/directives)
- [Data Protection Law](https://www.innovate.gov.et/proclamation)

### Helpful Guides
- [Taxpayer Guide](https://www.mor.gov.et/guides)
- [Business Registration Manual](https://www.motic.gov.et/manuals)
- [Consumer Rights Handbook](https://www.ethioconsumer.gov.et)

---
