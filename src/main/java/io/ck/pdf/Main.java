package io.ck.pdf;

import org.apache.pdfbox.io.RandomAccessReadBufferedFile;
import org.apache.pdfbox.pdfparser.PDFParser;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

import java.io.*;
import java.text.NumberFormat;
import java.text.ParseException;
import java.util.*;
import java.util.regex.Pattern;

public class Main {

    public static final Pattern PATTERN = Pattern.compile("^([0-9]+\\.[0-9]+\\.[0-9]+) (.+) (-?[0-9.]*[0-9]+,[0-9]+)$");
    public static final NumberFormat NUMBER_FORMAT = NumberFormat.getInstance(Locale.GERMANY);

    /**
     * Categories used to extract the data from the bank statement
     */
    public static final Map<String, Double> CATEGORIES = new HashMap<>();

    /**
     * Groups used to define group of categories which should be calculated and grouped together on printing.
     */
    public static final Map<String, List<String>> GROUPS = new HashMap<>();

    private static final String FILENAME_CATEGORIZED_VALUES = "categorized.csv";

    private static final String FILENAME_IMPORTANT_LINES = "rawData.csv";
    private static final String RAW_LINES_FILE_HEADERS = "file;date;category;subject;amount;";
    private static final String RAW_LINES_FILE_LINE = "%s;%s;%s;%s;%.2f;";
    private static final char CSV_DELIMITER = ';';

    public static final String OUT_KEY = "out";
    public static final String IN_KEY = "in";
    public static final String ALLOWED_FILE_NAME_REGEX = "girokonto";
    public static final String IGNORE_SALDO = "saldo";
    public static final String IGNORE_EXEMPTIO_ORDER = "freistellungsauftrag";
    public static final String IGNORE_SAVER_ORDER = "sparer-pauschbetrag";
    public static final Boolean ENABLE_LINE_LOGGING = false;


    static {
        CATEGORIES.put("amazon", 0.0);
        CATEGORIES.put("amaz", 0.0);
        CATEGORIES.put("paypal", 0.0);
        CATEGORIES.put("tank", 0.0);
        CATEGORIES.put("star", 0.0);
        CATEGORIES.put("hem", 0.0);
        CATEGORIES.put("total", 0.0);
        CATEGORIES.put("aral", 0.0);
        CATEGORIES.put("rewe", 0.0);
        CATEGORIES.put("kaufland", 0.0);
        CATEGORIES.put("edeka", 0.0);
        CATEGORIES.put("e-center", 0.0);
        CATEGORIES.put("dm", 0.0);
        CATEGORIES.put("rossmann", 0.0);
        CATEGORIES.put("aldi", 0.0);
        CATEGORIES.put("norma", 0.0);
        CATEGORIES.put("netto", 0.0);
        CATEGORIES.put("lidl", 0.0);
        CATEGORIES.put("dauerauftrag", 0.0);
        CATEGORIES.put("sparen", 0.0);
        CATEGORIES.put("versicherung", 0.0);
        CATEGORIES.put("vers.", 0.0);

        GROUPS.put("Grocery", List.of("rewe", "lidl", "edeka", "kaufland", "e-center", "dm", "rossmann", "aldi", "norma", "netto"));
        GROUPS.put("Amazon", List.of("amazon", "amzn"));
        GROUPS.put("Paypal", List.of("paypal"));
        GROUPS.put("Fuel", List.of("tank", "star", "hem", "total", "aral"));
        GROUPS.put("Standing order", List.of("dauerauftrag", "sparen"));
        GROUPS.put("Insurance", List.of("versicherung", "vers."));
    }

    public static final String CATEGORIZED_FILE_HEADERS = "title;in;out;"
            + String.join(Character.toString(CSV_DELIMITER), GROUPS.keySet());


    public static void main(String[] args) throws Exception {
        final var folder = new File("/home/cqjawa/Documents/ing");

        final var startTime = System.currentTimeMillis();
        System.out.println("Processing files in folder: " + folder.getAbsolutePath());
        System.out.println("Found files: " + Objects.requireNonNull(folder.listFiles()).length);
        System.out.println("Writing results to files: " + FILENAME_CATEGORIZED_VALUES + " and " + FILENAME_IMPORTANT_LINES);
        System.out.println("-----------------------------------");

        final var categorizedFile = new File(folder, FILENAME_CATEGORIZED_VALUES);
        try (FileWriter fw = new FileWriter(categorizedFile, true);
             BufferedWriter bw = new BufferedWriter(fw);
             PrintWriter categorizedDataWriter = new PrintWriter(bw)) {

            categorizedDataWriter.println(CATEGORIZED_FILE_HEADERS);

            final var importantLinesFile = new File(folder, FILENAME_IMPORTANT_LINES);
            try (FileWriter fw2 = new FileWriter(importantLinesFile, true);
                 BufferedWriter bw2 = new BufferedWriter(fw2);
                 PrintWriter importantLinesWriter = new PrintWriter(bw2)) {
                importantLinesWriter.println(RAW_LINES_FILE_HEADERS);

                for (var file : Objects.requireNonNull(folder.listFiles())) {
                    if (!file.getName().toLowerCase(Locale.GERMANY).endsWith(".pdf")) {
                        // skip non pdf files
                        System.out.println("Skipping non-pdf file: " + file.getName());
                        continue;
                    }

                    if (!file.getName().toLowerCase(Locale.GERMANY).startsWith(ALLOWED_FILE_NAME_REGEX)) {
                        System.out.println("Skipping non-girokonto file: " + file.getName());
                        // skip non girokonto files
                        continue;
                    }

                    System.out.println("Processing file: " + file.getName());

                    PDFParser parser = new PDFParser(new RandomAccessReadBufferedFile(file));
                    try (PDDocument document = parser.parse()) {
                        String text = new PDFTextStripper().getText(document);
                        final var bankData = convertBankStatements(file.getName(), text);
                        printCategorizedData(file, categorizedDataWriter, bankData.categorizedData);
                        bankData.importantLines.forEach(importantLinesWriter::println);
                    }
                }
            }
        }
        final var endTime = System.currentTimeMillis();
        System.out.println("-----------------------------------");
        System.out.println("Processing finished in " + (endTime - startTime) + " ms");
    }

    private static void printCategorizedData(File bankFile, PrintWriter writer,  Map<String, Double> categorizedData) {
        // header
        final var groups = GROUPS.keySet();

        // categorized values
        writer.println();
        writer.printf("%s%s", bankFile.getName(), CSV_DELIMITER);
        writer.printf("%.2f%s", categorizedData.get(IN_KEY), CSV_DELIMITER);
        writer.printf("%.2f%s", categorizedData.get(OUT_KEY), CSV_DELIMITER);

        groups.forEach(group -> {
            final var categories = GROUPS.get(group);
            final var amount =
                    categories.stream().map(categorizedData::get).filter(Objects::nonNull).mapToDouble(Double::doubleValue).sum();
            writer.printf("%.2f%s", amount, CSV_DELIMITER);
        });
    }

    /**
     * Converts a bank statements, to a map with specified categories.
     * @param text the text which contains all the bank statements
     * @return extracted bank data, containing important lines and a map which contains the categorized data
     */
    private static BankData convertBankStatements(String fileName, String text) {
        // init
        final var categories = new HashMap<>(CATEGORIES);
        categories.put(OUT_KEY, 0.0);
        categories.put(IN_KEY, 0.0);

        final List<String> importantLines = new ArrayList<>();

        text.lines().forEach(line -> {

            var matcher = PATTERN.matcher(line);
            if (!matcher.find()
                || line.toLowerCase(Locale.GERMANY).contains(IGNORE_SALDO)
                || line.toLowerCase(Locale.GERMANY).contains(IGNORE_EXEMPTIO_ORDER)
                || line.toLowerCase(Locale.GERMANY).contains(IGNORE_SAVER_ORDER)
            ) {
                return; // no amount go to next line
            }

            // lines add for

            try {
                final var value = NUMBER_FORMAT.parse(matcher.group(3)).doubleValue();
                if (value >= 0) {
                    categories.computeIfPresent(IN_KEY, (k, v) -> v + value);
                } else {
                    categories.computeIfPresent(OUT_KEY, (k, v) -> v + value);
                }

                final var subject = matcher.group(2);
                final var group = GROUPS
                        .entrySet()
                        .stream()
                        .filter(stringListEntry ->
                                stringListEntry.getValue().stream()
                                        .anyMatch(v ->
                                                subject.toLowerCase(Locale.GERMANY).contains(v)))
                        .map(Map.Entry::getKey).findAny().orElse("n/a");

                final var rawLine =
                        String.format(RAW_LINES_FILE_LINE,
                                fileName, // fileName
                                matcher.group(1), // date
                                group, // category
                                subject, // subject
                                value); // amount
                importantLines.add(rawLine);
                if (ENABLE_LINE_LOGGING) {
                    System.out.println(line);
                }

                CATEGORIES.keySet().stream()
                        .filter(category -> line.toLowerCase(Locale.GERMANY).contains(category))
                        .findAny().ifPresent(category -> categories.computeIfPresent(category, (k, v) -> v + value));
            } catch (ParseException e) {
                throw new RuntimeException(e);
            }
        });
        return new BankData(importantLines, categories);
    }

    private record BankData(List<String> importantLines, Map<String, Double> categorizedData) {

    }
}
