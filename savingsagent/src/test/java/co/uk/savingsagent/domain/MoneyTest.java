package co.uk.savingsagent.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class MoneyTest {

    @Test
    void parsesPoundsAndPence() {
        assertThat(Money.of("1234.56").pence()).isEqualTo(123456L);
        assertThat(Money.of("10")).isEqualTo(Money.ofPence(1000));
    }

    @Test
    void rejectsFractionsOfAPenny() {
        assertThatThrownBy(() -> Money.of("1.234")).isInstanceOf(ArithmeticException.class);
    }

    @Test
    void rejectsNegativeAmounts() {
        assertThatThrownBy(() -> Money.ofPence(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void addsAndSubtracts() {
        assertThat(Money.of("1.50").plus(Money.of("2.75"))).isEqualTo(Money.of("4.25"));
        assertThat(Money.of("4.25").minus(Money.of("1.50"))).isEqualTo(Money.of("2.75"));
    }

    @Test
    void subtractingMoreThanYouHaveFails() {
        assertThatThrownBy(() -> Money.of("1").minus(Money.of("2")))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void comparesAndPicksMinimum() {
        assertThat(Money.of("5").isGreaterThan(Money.of("4.99"))).isTrue();
        assertThat(Money.of("4.99").isLessThan(Money.of("5"))).isTrue();
        assertThat(Money.min(Money.of("5"), Money.of("4.99"))).isEqualTo(Money.of("4.99"));
    }

    @Test
    void equalityIgnoresHowItWasBuilt() {
        assertThat(Money.of("10.00")).isEqualTo(Money.ofPence(1000)).hasSameHashCodeAs(Money.of("10"));
    }

    @Test
    void printsAsPounds() {
        assertThat(Money.ofPence(123456).toString()).isEqualTo("£1234.56");
        assertThat(Money.ofPence(5).toString()).isEqualTo("£0.05");
    }

    // ---- your piece ----

    @Test
    void multipliesByARate() {
        assertThat(Money.of("10000").times(new BigDecimal("0.045"))).isEqualTo(Money.of("450.00"));
        assertThat(Money.of("1234.56").times(new BigDecimal("0.0395"))).isEqualTo(Money.of("48.77"));
    }

    @Test
    void roundsHalfPenniesToEven() {
        assertThat(Money.ofPence(25).times(new BigDecimal("0.5"))).isEqualTo(Money.ofPence(12));
        assertThat(Money.ofPence(35).times(new BigDecimal("0.5"))).isEqualTo(Money.ofPence(18));
    }

    @Test
    void negativeFactorIsRejected() {
        assertThatThrownBy(() -> Money.of("1").times(new BigDecimal("-0.5")))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
