# 🚨 PULSESTREAM DEVELOPMENT RULES - QUICK REFERENCE

## 📅 **Created**: August 22, 2025  
## ⚠️ **Status**: MANDATORY - Follow these rules NO MATTER WHAT  

---

## 🔴 **CORE RULES - NEVER VIOLATE**

### **1. NO TEST-DRIVEN CODE CHANGES** 🚫
- Never modify code just to pass tests
- Never adjust codebase for individual test cases
- Never make temporary fixes for test results

### **2. CODE DESIGN COMES FIRST** ✅
- Design APIs based on requirements, not tests
- Write code first, then write tests to validate
- Maintain consistent API contracts

### **3. PROTECT WORKING FUNCTIONALITY** 🛡️
- Never break working systems
- Preserve existing, proven functionality
- Test changes in isolation before integration

---

## 🚫 **FORBIDDEN PRACTICES**

- Adding methods just because tests need them
- Modifying function signatures to match test calls
- Changing data models for test convenience
- Adjusting business logic for test scenarios
- Writing tests that require code changes

---

## ✅ **REQUIRED PRACTICES**

- Review existing functionality before making changes
- Identify real requirements, not test-driven needs
- Design proper solutions following established patterns
- Plan integration points and ensure compatibility
- Document all changes with clear rationale

---

## 🛡️ **PROTECTED SYSTEMS (NEVER MODIFY)**

### **100% Working - PROTECTED**
1. **Authentication System** - JWT, multi-tenancy, user management
2. **Event Ingestion System** - Single/batch ingestion, validation, rate limiting
3. **REST API Endpoints** - Health, events, search, statistics
4. **Database & Storage** - PostgreSQL, Redis, CRUD operations

---

## 🔍 **CHANGE APPROVAL CHECKLIST**

Before making ANY changes, ask:
- [ ] Does this change address a real requirement?
- [ ] Is this change necessary for functionality?
- [ ] Does this change maintain backward compatibility?
- [ ] Does this change follow established patterns?
- [ ] Does this change have proper test coverage?
- [ ] Does this change not break working systems?

---

## ⚠️ **ENFORCEMENT CONSEQUENCES**

- **First violation**: Warning and education
- **Second violation**: Code review rejection
- **Third violation**: Development privileges review
- **Repeated violations**: Escalation to management

---

## 📞 **WHEN IN DOUBT**

1. **Ask yourself**: "Is this change for real functionality or just to pass a test?"
2. **Review existing code**: "How does this fit with current patterns?"
3. **Consult team**: "Does this change make sense architecturally?"
4. **Document decision**: "Why is this change necessary?"

---

## 🏁 **REMEMBER**

**These rules are NOT optional.** They protect:
- Working functionality
- Code quality
- System stability
- Team productivity
- Project success

**Follow them religiously. Your future self (and team) will thank you.**

---

*Full Rules Document: `progress/development-rules.md`*  
*Last Updated: August 22, 2025*  
*Status: ACTIVE - MUST FOLLOW*
