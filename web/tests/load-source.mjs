import { readFileSync } from 'node:fs'
import ts from 'typescript'

export function sourceUrl(path) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 }
  })
  const compiled = outputText.includes("from '../../http'")
    ? outputText.replace("from '../../http'", `from '${sourceUrl('../src/http.ts')}'`)
    : outputText
  return `data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`
}
