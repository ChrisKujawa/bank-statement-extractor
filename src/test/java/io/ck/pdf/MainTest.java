package io.ck.pdf;

import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class MainTest {

    private static void assertAmount(double expected, BigDecimal actual) {
        assertEquals(0, new BigDecimal(String.valueOf(expected)).compareTo(actual),
                "Expected " + expected + " but got " + actual);
    }

    @Test
    void parsesPositiveAmount() {
        // given
        String line = "01.01.2024 Gehalt Arbeitgeber 1.500,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(1500.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void parsesNegativeAmount() {
        // given
        String line = "05.01.2024 REWE Markt -49,99";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(-49.99, result.get("out"));
        assertAmount(0.00, result.get("in"));
    }

    @Test
    void accumulatesMultipleTransactions() {
        // given
        String text = "01.01.2024 Gehalt 1.000,00\n05.01.2024 REWE Markt -49,99\n10.01.2024 LIDL -12,49";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(text);

        // then
        assertAmount(1000.00, result.get("in"));
        assertAmount(-62.48, result.get("out"));
    }

    @Test
    void ignoresSaldoLines() {
        // given
        String line = "31.01.2024 Kontostand/Saldo -200,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(0.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void ignoresFreistellungsauftragLines() {
        // given
        String line = "01.01.2024 Freistellungsauftrag 801,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(0.00, result.get("in"));
    }

    @Test
    void ignoresSparerPauschbetragLines() {
        // given
        String line = "01.01.2024 Sparer-Pauschbetrag 100,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(0.00, result.get("in"));
    }

    @Test
    void nonMatchingLineIsIgnored() {
        // given
        String line = "This is not a transaction line";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(0.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void categorizesGroceryTransaction() {
        // given
        String line = "05.01.2024 REWE Markt -49,99";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(-49.99, result.get("rewe"));
    }

    @Test
    void doesNotFalsePositiveOnStar() {
        // given — "star" should NOT match "Sparkasse" (description-only matching)
        String line = "05.01.2024 Sparkasse Duisburg -100,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(0.00, result.get("star"));
    }

    @Test
    void doesNotFalsePositiveOnTank() {
        // given — "tank" SHOULD match "Tankstelle" in the description
        String line = "05.01.2024 Aral Tankstelle -60,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(-60.00, result.get("tank"));
    }

    @Test
    void columnOrderIsConsistentAcrossRuns() {
        // given / when
        var keys1 = java.util.List.copyOf(Main.GROUPS.keySet());
        var keys2 = java.util.List.copyOf(Main.GROUPS.keySet());

        // then
        assertEquals(keys1, keys2);
        assertEquals(java.util.List.of("Grocery", "Shopping", "Fuel", "Order"), keys1);
    }

    @Test
    void rejectsMalformedDateInLine() {
        // given
        String line = "1.2.3 Zahlung -50,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(0.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void acceptsValidGermanDate() {
        // given
        String line = "15.03.2024 Gehalt 2.000,00";

        // when
        Map<String, BigDecimal> result = Main.convertBankStatement(line);

        // then
        assertAmount(2000.00, result.get("in"));
    }
}
