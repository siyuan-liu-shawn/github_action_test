package scripts

import (
	"encoding/yaml"
	"strings"
	"tool/cli"
	"tool/exec"
	"tool/file"

	"github.com/kouzoh/dataplatform-kubernetes/pkg/k8s/core"
)

avro_tools: *"./avro-tools.jar" | string @tag(avro_tools)
idl_file:   *"./*.avdl" | string         @tag(idl_file)
output_dir: *"./" | string               @tag(output_dir)
schema_dir: *"./" | string               @tag(schema_dir)

avro_config_map: X=core.#ConfigMap & {
	_metadata: AvroMetadata
	_glob:     file.Glob & {
		glob: "\(schema_dir)*.avsc"
	}
	_data: {
		for _, f in X._glob.files {
			"\(f)": file.Read & {
				filename: f
				contents: string
			}
		}
	}

	metadata: X._metadata.metadata
	data: {
		for _, d in X._data {
			"\(strings.Replace(d.filename, schema_dir, "", -1))": d.contents
		}
	}
}

command: {
	avdl: {
		idl: file.Glob & {
			glob: idl_file
		}
		for _, f in idl.files {
			run: exec.Run & {
				cmd: ["java", "-jar", avro_tools, "idl2schemata", f, output_dir]
			}
		}
	}

	avsc: {
		print: cli.Print & {
			text: "\(output_dir)\(avro_config_map.metadata.name).yaml"
		}
		create: file.Create & {
			filename: "\(output_dir)\(avro_config_map.metadata.name).yaml"
			contents: yaml.Marshal(avro_config_map)
		}
	}
}
