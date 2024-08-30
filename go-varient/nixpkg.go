package main

import (
    "bufio"
    "context"
    "fmt"
    "io"
    "os"
    "os/exec"
    "strings"
)

const configFile = "/etc/nixos/configuration.nix"

func main() {
    if len(os.Args) < 2 || os.Args[1] == "--help" {
        printHelp()
        return
    }

    command := os.Args[1]
    args := os.Args[2:]

    switch command {
    case "install":
        if len(args) == 0 || args[0] == "--help" {
            fmt.Println("Usage: nixpkg install package1 [package2 ...]")
            return
        }
        modifyPackages(args, true)
    case "remove":
        if len(args) == 0 || args[0] == "--help" {
            fmt.Println("Usage: nixpkg remove package1 [package2 ...]")
            return
        }
        modifyPackages(args, false)
    case "update":
        if len(args) > 0 && args[0] == "--help" {
            fmt.Println("Usage: nixpkg update")
            return
        }
        updatePackages()
    case "search":
        if len(args) == 0 || args[0] == "--help" {
            fmt.Println("Usage: nixpkg search searchTerm")
            return
        }
        searchPackages(args[0])
    default:
        fmt.Println("Invalid command. Use --help for usage information.")
    }
}

func printHelp() {
    helpMessage := `
Usage: nixpkg [command]

Commands:
  install package1 [package2 ...]  Install one or more packages
  remove package1 [package2 ...]   Remove one or more packages
  update                           Update all packages
  search searchTerm                Search for a package
`
    fmt.Println(strings.TrimSpace(helpMessage))
}

func modifyPackages(packages []string, install bool) {
    file, err := os.ReadFile(configFile)
    if err != nil {
        fmt.Println("Error reading configuration file:", err)
        return
    }

    lines := strings.Split(string(file), "\n")
    var updatedLines []string
    inPackageSection, packageModified := false, false

    for _, line := range lines {
        trimmedLine := strings.TrimSpace(line)
        if strings.HasPrefix(trimmedLine, "environment.systemPackages") {
            inPackageSection = true
            updatedLines = append(updatedLines, line)
            continue
        }

        if inPackageSection && strings.Contains(trimmedLine, "]") {
            if install {
                for _, pkg := range packages {
                    pkgLine := "pkgs." + pkg
                    if !containsPackage(updatedLines, pkgLine) {
                        updatedLines = append(updatedLines, "    "+pkgLine)
                        packageModified = true
                    }
                }
            }
            inPackageSection = false
            updatedLines = append(updatedLines, line)
            continue
        } else if inPackageSection && !install {
            for _, pkg := range packages {
                if strings.Contains(trimmedLine, "pkgs."+pkg) {
                    packageModified = true
                    continue
                }
            }
        }

        if !inPackageSection || !install {
            updatedLines = append(updatedLines, line)
        }
    }

    if !packageModified {
        fmt.Println("No changes made to configuration.")
        return
    }

    err = os.WriteFile(configFile, []byte(strings.Join(updatedLines, "\n")), 0644)
    if err != nil {
        fmt.Println("Error writing to configuration file:", err)
        return
    }

    fmt.Println("Configuration updated successfully. Rebuilding NixOS...")
    rebuildCmd := exec.Command("sudo", "nixos-rebuild", "switch")
    if err := rebuildCmd.Run(); err != nil {
        fmt.Println("Error rebuilding NixOS:", err)
        return
    }

    fmt.Println("NixOS rebuilt successfully.")
}

func containsPackage(lines []string, packageLine string) bool {
    for _, line := range lines {
        if strings.Contains(line, packageLine) {
            return true
        }
    }
    return false
}

func updatePackages() {
    fmt.Println("Updating NixOS channels...")
    updateCmd := exec.Command("sudo", "nix-channel", "--update")
    updateCmd.Stdout = os.Stdout
    updateCmd.Stderr = os.Stderr
    if err := updateCmd.Run(); err != nil {
        fmt.Println("Error updating Nix channels:", err)
        return
    }

    fmt.Println("Rebuilding and upgrading NixOS...")
    rebuildCmd := exec.Command("sudo", "nixos-rebuild", "switch", "--upgrade")
    rebuildCmd.Stdout = os.Stdout
    rebuildCmd.Stderr = os.Stderr
    if err := rebuildCmd.Run(); err != nil {
        fmt.Println("Error rebuilding NixOS:", err)
        return
    }

    fmt.Println("NixOS updated successfully.")
}

func searchPackages(searchTerm string) {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    nixEnvCmd := exec.CommandContext(ctx, "nix-env", "-qaP")
    nixEnvOut, err := nixEnvCmd.StdoutPipe()
    if err != nil {
        fmt.Println("Error creating StdoutPipe for nix-env:", err)
        return
    }

    grepCmd := exec.CommandContext(ctx, "grep", searchTerm)
    grepIn, err := grepCmd.StdinPipe()
    if err != nil {
        fmt.Println("Error creating StdinPipe for grep:", err)
        return
    }

    grepOut, err := grepCmd.StdoutPipe()
    if err != nil {
        fmt.Println("Error creating StdoutPipe for grep:", err)
        return
    }

    if err := nixEnvCmd.Start(); err != nil {
        fmt.Println("Error starting nix-env command:", err)
        return
    }

    if err := grepCmd.Start(); err != nil {
        fmt.Println("Error starting grep command:", err)
        return
    }

    go func() {
        defer grepIn.Close()
        io.Copy(grepIn, nixEnvOut)
    }()

    scanner := bufio.NewScanner(grepOut)
    for scanner.Scan() {
        fmt.Println(scanner.Text())
    }

    if err := nixEnvCmd.Wait(); err != nil {
        fmt.Println("nix-env command did not finish successfully:", err)
    }
    if err := grepCmd.Wait(); err != nil {
        fmt.Println("grep command did not finish successfully:", err)
    }
}

