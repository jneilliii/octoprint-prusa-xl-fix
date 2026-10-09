$(function() {
    function PrusaXLToolFixViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.settings = undefined;
        self.printerList = ko.observableArray([]);
        self.loadError = ko.observable("");

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };

        self.selectedIds = function() {
            return ko.toJS(self.settings.plugins.prusaxltoolfix.printers) || [];
        };

        self.fallbackProfiles = function() {
            var node = document.getElementById("prusaxltoolfix_profiles_json");
            if (!node || !node.textContent) {
                return [];
            }
            try {
                var parsed = JSON.parse(node.textContent);
                return Array.isArray(parsed) ? parsed : [];
            } catch (exc) {
                return [];
            }
        };

        self.normalizeProfiles = function(entries) {
            var profiles = [];
            var seen = {};

            (entries || []).forEach(function(profile) {
                if (!profile) {
                    return;
                }
                var id = profile.id;
                if (typeof id !== "string" || !id) {
                    return;
                }
                if (seen[id]) {
                    return;
                }
                seen[id] = true;
                profiles.push({
                    id: id,
                    name: profile.name || id
                });
            });

            profiles.sort(function(a, b) {
                return a.name.localeCompare(b.name);
            });
            return profiles;
        };

        self.isEnabled = function(id, selected) {
            if (selected.indexOf("*") !== -1) {
                return true;
            }
            return selected.indexOf(id) !== -1;
        };

        self.setPrinterList = function(entries) {
            var selected = self.selectedIds();
            var profiles = self.normalizeProfiles(entries);

            // Keep previously selected ids that are no longer present so the
            // user can still see and clear them.
            selected.forEach(function(id) {
                if (id === "*") {
                    return;
                }
                if (profiles.some(function(profile) { return profile.id === id; })) {
                    return;
                }
                profiles.push({
                    id: id,
                    name: id + " (unavailable)"
                });
            });

            self.printerList(profiles.map(function(profile) {
                return {
                    id: profile.id,
                    name: profile.name,
                    enabled: ko.observable(self.isEnabled(profile.id, selected))
                };
            }));
        };

        self.loadPrinters = function() {
            self.loadError("");
            self.setPrinterList(self.fallbackProfiles());

            return OctoPrint.printerprofiles.list()
                .done(function(response) {
                    var listed = response && response.profiles ? response.profiles : {};
                    var entries = Array.isArray(listed)
                        ? listed
                        : Object.keys(listed).map(function(id) {
                            return listed[id];
                        });
                    if (entries.length) {
                        self.setPrinterList(entries);
                    } else if (!self.printerList().length) {
                        self.loadError("No printer profiles were returned by OctoPrint.");
                    }
                })
                .fail(function() {
                    if (!self.printerList().length) {
                        self.loadError("Could not load printer profiles.");
                    }
                });
        };

        self.onSettingsShown = function() {
            self.loadPrinters();
        };

        self.showPrinterProfiles = function() {
            $("#settings_printerProfiles_link a").tab("show");
            return false;
        };

        self.onSettingsBeforeSave = function() {
            var printers = self.printerList();
            var selected = [];

            printers.forEach(function(printer) {
                if (printer.enabled()) {
                    selected.push(printer.id);
                }
            });

            var available = printers.filter(function(printer) {
                return printer.name.indexOf(" (unavailable)") === -1;
            });
            var allSelected = available.length > 0
                && available.every(function(printer) {
                    return printer.enabled();
                })
                && selected.length === available.length;

            self.settings.plugins.prusaxltoolfix.printers(
                allSelected ? ["*"] : selected
            );
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PrusaXLToolFixViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_prusaxltoolfix"]
    });
});
