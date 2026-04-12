package io.ck.pdf;

import org.apache.pdfbox.io.RandomAccessReadBufferedFile;
import org.apache.pdfbox.pdfparser.PDFParser;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

import java.io.File;
import java.math.BigDecimal;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

public class Main {

    public static final Pattern PATTERN = Pattern.compile("^([0-3][0-9]\\.[0-1][0-9]\\.[0-9]{4}) (.+) (-?[0-9.]*[0-9]+,[0-9]+)$");

    /**
     * Categories used to extract the data from the bank statement
     */
    public static final Map<String, BigDecimal> CATEGORIES;

    /**
     * Groups used to define group of categories which should be calculated and grouped together on printing.
     */
    public static final Map<String, List<String>> GROUPS;

    public static final String OUT_KEY = "out";
    public static final String IN_KEY = "in";
    public static final String IGNORE_SALDO = "saldo";
    public static final String IGNORE_EXEMPTION_ORDER = "freistellungsauftrag";
    public static final String IGNORE_SAVER_ORDER = "sparer-pauschbetrag";
    public static final boolean ENABLE_LINE_LOGGING = false;

    static {
        var cats = new LinkedHashMap<String, BigDecimal>();
        cats.put("amazon", BigDecimal.ZERO);
        cats.put("paypal", BigDecimal.ZERO);
        cats.put("tank", BigDecimal.ZERO);
        cats.put("rewe", BigDecimal.ZERO);
        cats.put("kaufland", BigDecimal.ZERO);
        cats.put("edeka", BigDecimal.ZERO);
        cats.put("lidl", BigDecimal.ZERO);
        cats.put("star", BigDecimal.ZERO);
        cats.put("dauerauftrag", BigDecimal.ZERO);
        CATEGORIES = Collections.unmodifiableMap(cats);

        var groups = new LinkedHashMap<String, List<String>>();
        groups.put("Grocery", List.of("rewe", "lidl", "edeka", "kaufland"));
        groups.put("Shopping", List.of("amazon", "paypal"));
        groups.put("Fuel", List.of("tank", "star"));
        groups.put("Order", List.of("dauerauftrag"));
        GROUPS = Collections.unmodifiableMap(groups);
    }

    public static void main(String[] args) throws Exception {
        String path = args.length > 0 ? args[0] : "/tmp/bank.pdf";
        File file = new File(path);
        try (var raf = new RandomAccessReadBufferedFile(file);
             PDDocument document = new PDFParser(raf).parse()) {
            String text = new PDFTextStripper().getText(document);
            final var bankData = convertBankStatement(text);
            printData(file, bankData);
        }
    }

    private static void printData(File file, Map<String, BigDecimal> bankData) {
        // header
        System.out.printf("title %s %s ", IN_KEY, OUT_KEY);
        final var groups = GROUPS.keySet();
        groups.forEach(category -> System.out.printf("%s ", category));
        System.out.println();

        // values
        System.out.printf("%s ", file.getName());
        System.out.printf("%.2f ", bankData.getOrDefault(IN_KEY, BigDecimal.ZERO));
        System.out.printf("%.2f ", bankData.getOrDefault(OUT_KEY, BigDecimal.ZERO));

        groups.forEach(group -> {
            final var categories = GROUPS.get(group);
            final var amount = categories.stream()
                    .map(c -> bankData.getOrDefault(c, BigDecimal.ZERO))
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            System.out.printf("%.2f ", amount);
        });
        System.out.println();
    }

    /**
     * Converts a bank statement, to a map with specified categories.
     * @param text the text which contains all the bank statement details
     * @return a map which contains the categorized data
     */
    static Map<String, BigDecimal> convertBankStatement(String text) {
        // init
        final var categories = new LinkedHashMap<String, BigDecimal>();
        CATEGORIES.keySet().forEach(k -> categories.put(k, BigDecimal.ZERO));
        categories.put(OUT_KEY, BigDecimal.ZERO);
        categories.put(IN_KEY, BigDecimal.ZERO);

        text.lines().forEach(line -> {
            var matcher = PATTERN.matcher(line);
            if (!matcher.find()
                || line.toLowerCase(Locale.GERMANY).contains(IGNORE_SALDO)
                || line.toLowerCase(Locale.GERMANY).contains(IGNORE_EXEMPTION_ORDER)
                || line.toLowerCase(Locale.GERMANY).contains(IGNORE_SAVER_ORDER)
            ) {
                return;
            }

            final var rawAmount = matcher.group(3)
                    .replace(".", "")
                    .replace(",", ".");
            final var value = new BigDecimal(rawAmount);

            if (value.signum() >= 0) {
                categories.merge(IN_KEY, value, BigDecimal::add);
            } else {
                categories.merge(OUT_KEY, value, BigDecimal::add);
            }

            if (ENABLE_LINE_LOGGING) {
                System.out.println(line);
            }

            final var description = matcher.group(2).toLowerCase(Locale.GERMANY);
            CATEGORIES.keySet().stream()
                    .filter(category -> description.contains(category))
                    .findFirst()
                    .ifPresent(category -> categories.merge(category, value, BigDecimal::add));
        });
        return categories;
    }
}
