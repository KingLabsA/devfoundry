import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Safe markdown renderer (react-markdown escapes HTML by default) with GFM
 *  tables/strikethrough. Links open externally. Used for research reports and
 *  spec/architecture artifacts. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">{children}</a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
