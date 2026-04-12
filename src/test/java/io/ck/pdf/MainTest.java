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
        String line = "01.01.2024 Gehalt Arbeitgeber 1.500,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(1500.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void parsesNegativeAmount() {
        String line = "05.01.2024 REWE Markt -49,99";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(-49.99, result.get("out"));
        assertAmount(0.00, result.get("in"));
    }

    @Test
    void accumulatesMultipleTransactions() {
        String text = "01.01.2024 Gehalt 1.000,00\n05.01.2024 REWE Markt -49,99\n10.01.2024 LIDL -12,49";
        Map<String, BigDecimal> result = Main.convertBankStatement(text);
        assertAmount(1000.00, result.get("in"));
        assertAmount(-62.48, result.get("out"));
    }

    @Test
    void ignoresSaldoLines() {
        String line = "31.01.2024 Kontostand/Saldo -200,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(0.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void ignoresFreistellungsauftragLines() {
        String line = "01.01.2024 Freistellungsauftrag 801,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(0.00, result.get("in"));
    }

    @Test
    void ignoresSparerPauschbetragLines() {
        String line = "01.01.2024 Sparer-Pauschbetrag 100,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(0.00, result.get("in"));
    }

    @Test
    void nonMatchingLineIsIgnored() {
        String line = "This is not a transaction line";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(0.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void categorizesGroceryTransaction() {
        String line = "05.01.2024 REWE Markt -49,99";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(-49.99, result.get("rewe"));
    }

    @Test
    void doesNotFalsePositiveOnStar() {
        // "star" should NOT match "Sparkasse" — description-only matching
        String line = "05.01.2024 Sparkasse Duisburg -100,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(0.00, result.get("star"));
    }

    @Test
    void doesNotFalsePositiveOnTank() {
        // "tank" SHOULD match "Tankstelle" in the description
        String line = "05.01.2024 Aral Tankstelle -60,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(-60.00, result.get("tank"));
    }

    @Test
    void columnOrderIsConsistentAcrossRuns() {
        var keys1 = java.util.List.copyOf(Main.GROUPS.keySet());
        var keys2 = java.util.List.copyOf(Main.GROUPS.keySet());
        assertEquals(keys1, keys2);
        assertEquals(java.util.List.of("Grocery", "Shopping", "Fuel", "Order"), keys1);
    }

    @Test
    void rejectsMalformedDateInLine() {
        String line = "1.2.3 Zahlung -50,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(0.00, result.get("in"));
        assertAmount(0.00, result.get("out"));
    }

    @Test
    void acceptsValidGermanDate() {
        String line = "15.03.2024 Gehalt 2.000,00";
        Map<String, BigDecimal> result = Main.convertBankStatement(line);
        assertAmount(2000.00, result.get("in"));
    }
}
