# 🚨 PULSESTREAM DEVELOPMENT RULES - MUST FOLLOW

## 📅 **Created**: August 22, 2025  
## 🎯 **Purpose**: Prevent test-driven code changes and maintain proper software development practices  
## ⚠️ **Status**: MANDATORY - These rules must be followed NO MATTER WHAT  

---

## 🔴 **CRITICAL RULES - NEVER VIOLATE**

### **1. NO TEST-DRIVEN CODE CHANGES** 🚫
- **NEVER** modify existing code just to pass a specific test
- **NEVER** adjust the entire codebase for individual test cases
- **NEVER** make temporary fixes just to get green test results
- **NEVER** change API contracts to match test expectations

### **2. CODE DESIGN COMES FIRST** ✅
- **ALWAYS** design APIs and functionality based on requirements
- **ALWAYS** write code first, then write tests to validate it
- **ALWAYS** maintain consistent API contracts regardless of test cases
- **ALWAYS** follow established architectural patterns

### **3. PROTECT WORKING FUNCTIONALITY** 🛡️
- **NEVER** break working systems to accommodate new tests
- **ALWAYS** preserve existing, proven functionality
- **NEVER** make changes that could destabilize core features
- **ALWAYS** test changes in isolation before integration

---

## 📋 **DEVELOPMENT WORKFLOW RULES**

### **Phase 1: Design & Implementation** 🎨
1. **Define requirements clearly**
2. **Design API contracts and data models**
3. **Implement functionality following established patterns**
4. **Write comprehensive tests for the implementation**
5. **Validate against requirements, not test convenience**

### **Phase 2: Testing & Validation** 🧪
1. **Write tests that validate the design**
2. **Ensure tests cover edge cases and error conditions**
3. **Run tests to verify functionality works as designed**
4. **Fix only legitimate bugs, not test mismatches**

### **Phase 3: Integration & Deployment** 🚀
1. **Integrate new features with existing systems**
2. **Run full system tests to ensure stability**
3. **Deploy only after comprehensive validation**
4. **Monitor for any regressions**

---

## 🚫 **FORBIDDEN PRACTICES**

### **Code Changes** ❌
- Adding methods just because tests need them
- Modifying function signatures to match test calls
- Changing data models for test convenience
- Adjusting business logic for test scenarios

### **Test Modifications** ❌
- Writing tests that require code changes
- Modifying tests to work with broken code
- Creating tests that don't validate real functionality
- Using tests as a substitute for proper design

### **API Modifications** ❌
- Changing API contracts for test compatibility
- Modifying response formats for test convenience
- Adjusting authentication flows for test scenarios
- Changing data structures for test requirements

---

## ✅ **REQUIRED PRACTICES**

### **Before Making Any Changes** 🔍
1. **Review existing functionality** - understand what's working
2. **Identify real requirements** - not test-driven needs
3. **Design proper solutions** - follow established patterns
4. **Plan integration points** - ensure compatibility
5. **Document changes** - maintain clear records

### **When Writing Tests** 📝
1. **Test existing functionality** - don't require changes
2. **Validate API contracts** - ensure consistency
3. **Cover edge cases** - test real scenarios
4. **Maintain independence** - tests should not affect each other

### **When Fixing Issues** 🔧
1. **Identify root cause** - not just symptoms
2. **Fix the actual problem** - not test expectations
3. **Maintain backward compatibility** - don't break existing features
4. **Test thoroughly** - ensure no regressions

---

## 📊 **CURRENT WORKING SYSTEMS - PROTECT AT ALL COSTS**

### **✅ 100% Operational Systems** 🟢
1. **Authentication System** - JWT, multi-tenancy, user management
2. **Event Ingestion System** - Single/batch ingestion, validation, rate limiting
3. **REST API Endpoints** - Health, events, search, statistics
4. **Database & Storage** - PostgreSQL, Redis, CRUD operations

### **⚠️ Systems with Minor Issues** 🟡
1. **Dashboard System** - 57.1% working (core features operational)
2. **Alert Management** - 27.3% working (basic functionality working)

### **🛡️ Protection Rules**
- **NEVER** modify working authentication code
- **NEVER** change event ingestion logic
- **NEVER** modify working REST API endpoints
- **NEVER** alter database schemas or models
- **ONLY** fix legitimate bugs, not test mismatches

---

## 🎯 **EXTERNAL API TESTING RULES**

### **Integration Testing** 🔗
1. **Use existing, working APIs** - don't modify them
2. **Test real functionality** - not test scenarios
3. **Validate performance** - ensure scalability
4. **Test error handling** - real error conditions

### **API Contract Validation** 📋
1. **Verify request/response formats** - use existing contracts
2. **Test authentication flows** - use working JWT system
3. **Validate rate limiting** - use existing mechanisms
4. **Test multi-tenancy** - use proven isolation

---

## 📝 **CHANGE APPROVAL PROCESS**

### **For Any Code Changes** 🔐
1. **Document the requirement** - why is this change needed?
2. **Review existing functionality** - what will this affect?
3. **Design the solution** - how will this integrate?
4. **Plan testing strategy** - how will we validate?
5. **Get approval** - changes must be justified

### **Emergency Fixes** 🚨
- **ONLY** for critical production issues
- **MUST** be documented immediately
- **MUST** be reviewed within 24 hours
- **MUST** follow proper testing before deployment

---

## 🔍 **CODE REVIEW CHECKLIST**

### **Before Approving Any Changes** ✅
- [ ] **Does this change address a real requirement?**
- [ ] **Is this change necessary for functionality?**
- [ ] **Does this change maintain backward compatibility?**
- [ ] **Does this change follow established patterns?**
- [ ] **Does this change have proper test coverage?**
- [ ] **Does this change not break working systems?**

### **Red Flags - Reject Changes** 🚩
- [ ] **Change made just to pass a test**
- [ ] **Change modifies working functionality unnecessarily**
- [ ] **Change doesn't follow established patterns**
- [ ] **Change lacks proper documentation**
- [ ] **Change hasn't been tested thoroughly**

---

## 📚 **REFERENCES & EXAMPLES**

### **Examples of WRONG Approaches** ❌
```python
# WRONG: Adding method just for test
class UserService:
    def get_user_by_username(self, username):  # Added just for test
        pass

# WRONG: Modifying API for test convenience
def create_user(self, username, email):  # Changed signature for test
    pass
```

### **Examples of RIGHT Approaches** ✅
```python
# RIGHT: Method designed for real functionality
class UserService:
    def get_user_by_identifier(self, identifier_type, value):
        # Handles username, email, ID, etc.
        pass

# RIGHT: API designed for real use cases
def create_user(self, user_data):
    # Accepts structured user data
    pass
```

---

## 🎯 **ENFORCEMENT**

### **Team Responsibilities** 👥
- **Developers**: Follow these rules strictly
- **Testers**: Write tests for existing functionality
- **Reviewers**: Enforce these rules in code reviews
- **Leads**: Ensure compliance across the team

### **Violation Consequences** ⚠️
- **First violation**: Warning and education
- **Second violation**: Code review rejection
- **Third violation**: Development privileges review
- **Repeated violations**: Escalation to management

---

## 📞 **QUESTIONS & CLARIFICATIONS**

### **When in Doubt** 🤔
1. **Ask yourself**: "Is this change for real functionality or just to pass a test?"
2. **Review existing code**: "How does this fit with current patterns?"
3. **Consult team**: "Does this change make sense architecturally?"
4. **Document decision**: "Why is this change necessary?"

### **Contact Points** 📧
- **Technical Lead**: For architectural decisions
- **Team Lead**: For process questions
- **Documentation**: For rule clarifications

---

## 🏁 **CONCLUSION**

**These rules are NOT optional.** They are designed to:
- **Protect working functionality**
- **Maintain code quality**
- **Prevent technical debt**
- **Ensure proper development practices**
- **Build a stable, maintainable system**

**Follow them religiously. Your future self (and team) will thank you.**

---

*Last Updated: August 22, 2025*  
*Next Review: September 22, 2025*  
*Status: ACTIVE - MUST FOLLOW*
