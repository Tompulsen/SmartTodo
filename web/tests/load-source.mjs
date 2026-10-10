import { readFileSync } from 'node:fs'
import ts from 'typescript'

export function sourceUrl(path) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 }
  })
  const compiled = outputText.replace(/from '(\.[^']+)'/g, (_, specifier) => {
    const dependency = new URL(`${specifier}.ts`, new URL(path, import.meta.url))
    return `from '${sourceUrl(dependency)}'`
  })
  return `data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`
}
