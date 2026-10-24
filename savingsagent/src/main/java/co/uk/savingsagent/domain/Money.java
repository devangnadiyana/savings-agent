package co.uk.savingsagent.domain;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** Pounds sterling as whole pence. Immutable. Never negative. */
public record Money(long pence) implements Comparable<Money> {

    public static final Money ZERO = new Money(0);

    public Money {
        if (pence < 0) {
            throw new IllegalArgumentException("Money cannot be negative: " + pence + " pence");
        }
    }

    /** Parses "1234.56". Rejects fractions of a penny such as "1.234". */
    public static Money of(String pounds) {
        BigDecimal exact = new BigDecimal(pounds).setScale(2, RoundingMode.UNNECESSARY);
        return new Money(exact.movePointRight(2).longValueExact());
    }

    public static Money ofPence(long pence) {
        return new Money(pence);
    }

    public Money plus(Money other) {
        return new Money(Math.addExact(pence, other.pence));
    }

    /** Fails if the result would be negative. */
    public Money minus(Money other) {
        return new Money(Math.subtractExact(pence, other.pence));
    }

    /**
     * Multiplies by a factor such as 0.045 (meaning 4.5%) and rounds to the
     * nearest penny, HALF_EVEN. YOUR PIECE — spec below.
     */
    public Money times(BigDecimal factor) {
        throw new UnsupportedOperationException("not written yet");
    }

    public boolean isGreaterThan(Money other) {
        return pence > other.pence;
    }

    public boolean isLessThan(Money other) {
        return pence < other.pence;
    }

    public static Money min(Money a, Money b) {
        return a.pence <= b.pence ? a : b;
    }

    public BigDecimal asPounds() {
        return BigDecimal.valueOf(pence, 2);
    }

    @Override
    public int compareTo(Money other) {
        return Long.compare(pence, other.pence);
    }

    @Override
    public String toString() {
        return "£" + asPounds().toPlainString();
    }
}
