package co.uk.savingsagent.domain;

public enum AccessType {
    EASY_ACCESS,
    NOTICE,
    FIXED_TERM;

    public boolean isInstantAccess() {
        return this == EASY_ACCESS;
    }
}
