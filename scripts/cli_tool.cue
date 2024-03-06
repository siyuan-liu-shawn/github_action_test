package scripts

import (
	"encoding/yaml"
	"tool/cli"

	"github.com/kouzoh/dataplatform-kubernetes/pkg/k8s"
)

command: dump: cli.Print & {
	text: yaml.MarshalStream( [ for o in k8s.#InstallOrder for r in Delivery.resources if r.kind == o {r}])
}
