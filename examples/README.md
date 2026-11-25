# Example configurations

- `saas/`: full-stack private project register, quick discovery.
- `ecommerce/`: product/price/stock register, advanced discovery; checkout remains an extension.
- `inventory/`: backend-only inventory API with SKU/quantity/location fields.
- `portfolio/`: design-only static portfolio-management concept with sample data.

Initialize a separate workspace, then import an example:

```sh
python -m appforge --workspace my-demo init
python -m appforge --workspace my-demo import examples/saas/project.config.json
python -m appforge --workspace my-demo plan
```

Import records values as imported decisions. Review the plan and preview before approve/generate. These examples contain no credentials or production data. Runtime limitations and unimplemented domain extensions are carried in their selected blueprints.
