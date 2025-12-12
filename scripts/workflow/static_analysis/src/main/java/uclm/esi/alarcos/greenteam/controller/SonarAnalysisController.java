package uclm.esi.alarcos.greenteam.energy_aware_devops_web.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.FileSystemUtils;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

@RestController
@RequestMapping("/api/sonar")
public class SonarAnalysisController {

    private final String TEMP_DIR = System.getProperty("java.io.tmpdir");

    @PostMapping(value = "/analyze", consumes = "multipart/form-data", produces = "text/plain")
    public ResponseEntity<String> analyzeProject(
            @RequestParam("repoZip") MultipartFile repoZip,
            @RequestParam("projectKey") String projectKey,
            @RequestParam("organization") String organization,
            @RequestParam(value = "branch", defaultValue = "main") String branch,
            @RequestHeader("Authorization") String authorizationHeader
    ) {
        if (repoZip.isEmpty() || projectKey == null || organization == null || authorizationHeader == null) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body("Missing parameters");
        }

        String token;
        if (authorizationHeader.toLowerCase().startsWith("bearer ")) {
            token = authorizationHeader.substring(7).trim();
        } else {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body("Authorization header invalid");
        }

        Path tempRepoDir = null;

        try {
            tempRepoDir = Files.createTempDirectory(Paths.get(TEMP_DIR), "sonar_repo_");

            Path zipPath = tempRepoDir.resolve("repo.zip");
            Files.write(zipPath, repoZip.getBytes());

            unzip(zipPath.toFile(), tempRepoDir.toFile());

            File[] subdirs = tempRepoDir.toFile().listFiles(File::isDirectory);
            String sonarSources = ".";
            if (subdirs != null && subdirs.length == 1) {
                File rootFolder = subdirs[0];
                System.out.println("Carpeta raíz del repo: " + rootFolder.getName());
                sonarSources = rootFolder.getName();
            }
            System.out.println("sonar.sources = " + sonarSources);

            Path sonarProps = tempRepoDir.resolve("sonar-project.properties");
            String propertiesContent = String.format(
                    "sonar.projectKey=%s%n" +
                    "sonar.organization=%s%n" +
                    "sonar.host.url=https://sonarcloud.io%n" +
                    "sonar.sources=%s%n" +
                    "sonar.branch.name=%s%n",
                    projectKey, organization, sonarSources, branch
            );
            Files.write(sonarProps, propertiesContent.getBytes(StandardCharsets.UTF_8));
            System.out.println("sonar-project.properties created in: " + sonarProps);

            String dockerCommand = String.format(
                    "docker run --rm -e SONAR_TOKEN=\"%s\" -v \"%s:/usr/src\" sonarsource/sonar-scanner-cli",
                    token,
                    tempRepoDir.toAbsolutePath().toString().replace("\\", "/")
            );
            System.out.println("Executing docker: " + dockerCommand);

            Process process = Runtime.getRuntime().exec(dockerCommand);

            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            BufferedReader errorReader = new BufferedReader(new InputStreamReader(process.getErrorStream()));
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append(System.lineSeparator());
            }
            while ((line = errorReader.readLine()) != null) {
                output.append(line).append(System.lineSeparator());
            }

            int exitCode = process.waitFor();
            output.append("\nExit code: ").append(exitCode);
            System.out.println("SonarCloud analysis completed, exit code: " + exitCode);

            return ResponseEntity.ok(output.toString());

        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Error SonarCloud analysis: " + e.getMessage());
        } finally {
            if (tempRepoDir != null) {
                try {
                    FileSystemUtils.deleteRecursively(tempRepoDir);
                    System.out.println("Directorio temporal eliminado");
                } catch (IOException ignored) {}
            }
        }
    }

    private void unzip(File zipFile, File destDir) throws IOException {
        try (ZipInputStream zis = new ZipInputStream(new FileInputStream(zipFile))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                File newFile = new File(destDir, entry.getName());
                if (entry.isDirectory()) {
                    newFile.mkdirs();
                } else {
                    new File(newFile.getParent()).mkdirs();
                    try (FileOutputStream fos = new FileOutputStream(newFile)) {
                        byte[] buffer = new byte[4096];
                        int len;
                        while ((len = zis.read(buffer)) > 0) {
                            fos.write(buffer, 0, len);
                        }
                    }
                }
                zis.closeEntry();
            }
        }
    }
}

