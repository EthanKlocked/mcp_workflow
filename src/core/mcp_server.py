import os
import json
from dotenv import load_dotenv
from fastmcp import FastMCP
from ability.module.bitget_trader import BitgetAPI  
load_dotenv()

mcp = FastMCP("mcp-tools-server", stateless_http=True)

def get_bitget_client():
    api_key = os.getenv("BITGET_API_KEY")
    secret_key = os.getenv("BITGET_SECRET_KEY")
    passphrase = os.getenv("BITGET_PASSPHRASE")    
    if not all([api_key, secret_key, passphrase]):
        raise ValueError("Bitget API credentials not found in environment variables")    
    return BitgetAPI(
        api_key=api_key,
        secret=secret_key,
        passphrase=passphrase
    )

@mcp.tool()
async def get_bitget_account_info() -> str:
    """
    Get Bitget futures account information including balance and positions.
    """
    try:
        client = get_bitget_client()
        account_info = client.get_account_info()
        return json.dumps(account_info, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_bitget_positions() -> str:
    """
    Get all current positions in Bitget futures account.
    """
    try:
        client = get_bitget_client()
        positions = client.get_all_positions()
        return json.dumps(positions, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_bitget_price(symbol: str) -> str:
    """
    Get current price information for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
    """
    try:
        client = get_bitget_client()
        price_info = client.get_future_price(symbol.upper())
        return json.dumps(price_info, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_bitget_candles(symbol: str, interval: str = "1h", limit: int = 100) -> str:
    """
    Get candlestick data for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
        interval: Time interval (1m, 3m, 15m, 30m, 1h, 4h, 6h, 12h, 1d)
        limit: Number of candles to retrieve (max 1000, default 100)
    """
    try:
        client = get_bitget_client()
        candles = client.get_future_prices(
            symbol=symbol.upper(),
            interval=interval,
            limit=limit
        )
        return json.dumps(candles, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_bitget_open_orders(symbol: str = None) -> str:
    """
    Get all open orders for a specific symbol or all symbols.
    
    Args:
        symbol: Trading symbol (optional, e.g., BTCUSDT, ETHUSDT)
    """
    try:
        client = get_bitget_client()
        if symbol:
            orders = client.get_open_orders(symbol=symbol.upper())
        else:
            orders = client.get_open_orders()
        return json.dumps(orders, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def place_bitget_order(
    symbol: str,
    side: str,
    quantity: str,
    order_type: str = "MARKET",
    price: str = None
) -> str:
    """
    Place a futures order on Bitget.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
        side: Order side (BUY or SELL)
        quantity: Order quantity as string
        order_type: Order type (MARKET or LIMIT, default MARKET)
        price: Order price for LIMIT orders (required for LIMIT orders)
    """
    try:
        client = get_bitget_client()
        
        # 파라미터 검증
        if order_type.upper() == "LIMIT" and not price:
            return json.dumps({"error": "Price is required for LIMIT orders"}, ensure_ascii=False, indent=2)
        
        order_result = client.post_order(
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            _type=order_type.upper(),
            price=price
        )
        return json.dumps(order_result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def cancel_bitget_order(symbol: str, order_id: str = None, client_oid: str = None) -> str:
    """
    Cancel a futures order on Bitget.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
        order_id: Order ID (either order_id or client_oid is required)
        client_oid: Client order ID (either order_id or client_oid is required)
    """
    try:
        client = get_bitget_client()
        
        if not order_id and not client_oid:
            return json.dumps({"error": "Either order_id or client_oid is required"}, ensure_ascii=False, indent=2)
        
        cancel_result = client.delete_order(
            symbol=symbol.upper(),
            order_id=order_id,
            client_oid=client_oid
        )
        return json.dumps(cancel_result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def set_bitget_leverage(symbol: str, leverage: str) -> str:
    """
    Set leverage for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
        leverage: Leverage value as string (e.g., "10", "20")
    """
    try:
        client = get_bitget_client()
        leverage_result = client.set_leverage(
            symbol=symbol.upper(),
            leverage=leverage
        )
        return json.dumps(leverage_result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_bitget_order_history(symbol: str = None, limit: int = 50) -> str:
    """
    Get order history for a specific symbol or all symbols.
    
    Args:
        symbol: Trading symbol (optional, e.g., BTCUSDT, ETHUSDT)
        limit: Number of orders to retrieve (max 100, default 50)
    """
    try:
        client = get_bitget_client()
        if symbol:
            history = client.get_order_history(symbol=symbol.upper(), limit=limit)
        else:
            history = client.get_order_history(limit=limit)
        return json.dumps(history, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_env_info() -> str:
    """
    Returns selected environment variables for debugging purposes.
    Sensitive values are excluded.
    """
    allowed_keys = [
        "MCP_SERVER_HOST",
        "MCP_SERVER_PORT",
    ]
    env_info = {key: os.getenv(key) for key in allowed_keys if os.getenv(key) is not None}
    return json.dumps(env_info, ensure_ascii=False, indent=2)

@mcp.tool()
async def close_all_bitget_positions_correct() -> str:
    """
    Close all open positions using correct Bitget API parameters.
    """
    try:
        client = get_bitget_client()        
        positions = client.get_all_positions()        
        if "data" not in positions or positions.get("code") != "00000":
            return json.dumps({"error": "Failed to get positions", "response": positions}, ensure_ascii=False, indent=2)        
        active_positions = []
        close_orders = []        
        for pos in positions["data"]:
            total = float(pos.get("total", "0"))  
            hold_side = pos.get("holdSide", "")  
            if total > 0 and hold_side in ["long", "short"]:
                active_positions.append(pos)        
        if not active_positions:
            return json.dumps({"message": "No open positions to close"}, ensure_ascii=False, indent=2)        
        for pos in active_positions:
            symbol = pos.get("symbol", "")
            total_size = pos.get("total", "0")  
            hold_side = pos.get("holdSide", "")  
            margin_mode = pos.get("marginMode", "isolated")  
            margin_coin = pos.get("marginCoin", "USDT")
            close_side = "sell" if hold_side == "long" else "buy"            
            try:
                close_order = client.post_order(
                    symbol=symbol,
                    side=close_side.upper(),  
                    quantity=total_size,
                    _type="MARKET",
                    reduce_only=True,  
                    margin_mode=margin_mode,
                    margin_coin=margin_coin
                )                
                close_orders.append({
                    "symbol": symbol,
                    "position_size": total_size,
                    "hold_side": hold_side,
                    "close_side": close_side,
                    "margin_mode": margin_mode,
                    "close_order": close_order,
                    "success": close_order.get("code") == "00000"
                })                
            except Exception as order_error:
                close_orders.append({
                    "symbol": symbol,
                    "position_size": total_size,
                    "error": str(order_error),
                    "position_data": pos
                })        
        successful_orders = [o for o in close_orders if o.get("success") == True]
        failed_orders = [o for o in close_orders if "error" in o or o.get("success") != True]        
        return json.dumps({
            "action": "close_all_positions",
            "total_positions_found": len(active_positions),
            "successful_orders": len(successful_orders),
            "failed_orders": len(failed_orders),
            "close_orders": close_orders
        }, ensure_ascii=False, indent=2)        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def close_bitget_position_correct(symbol: str) -> str:
    """
    Close specific position using correct Bitget API parameters.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
    """
    try:
        client = get_bitget_client()        
        positions = client.get_all_positions()        
        if "data" not in positions or positions.get("code") != "00000":
            return json.dumps({"error": "Failed to get positions"}, ensure_ascii=False, indent=2)        
        target_position = None
        for pos in positions["data"]:
            if pos.get("symbol", "").upper() == symbol.upper():
                total = float(pos.get("total", "0"))
                hold_side = pos.get("holdSide", "")                
                if total > 0 and hold_side in ["long", "short"]:
                    target_position = pos
                    break        
        if not target_position:
            return json.dumps({"message": f"No open position found for {symbol}"}, ensure_ascii=False, indent=2)        
        symbol_name = target_position.get("symbol", "")
        total_size = target_position.get("total", "0")
        hold_side = target_position.get("holdSide", "")
        margin_mode = target_position.get("marginMode", "isolated")
        margin_coin = target_position.get("marginCoin", "USDT")        
        close_side = "sell" if hold_side == "long" else "buy"        
        close_order = client.post_order(
            symbol=symbol_name,
            side=close_side.upper(),
            quantity=total_size,
            _type="MARKET",
            reduce_only=True,
            margin_mode=margin_mode,
            margin_coin=margin_coin
        )        
        return json.dumps({
            "action": "position_closed",
            "symbol": symbol_name,
            "position_size": total_size,
            "hold_side": hold_side,
            "close_side": close_side,
            "margin_mode": margin_mode,
            "margin_coin": margin_coin,
            "original_position": target_position,
            "close_order": close_order,
            "success": close_order.get("code") == "00000"
        }, ensure_ascii=False, indent=2)        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def show_position_details() -> str:
    """
    Show detailed position information for debugging.
    """
    try:
        client = get_bitget_client()
        positions = client.get_all_positions()        
        if "data" not in positions:
            return json.dumps({"error": "No position data"}, ensure_ascii=False, indent=2)        
        position_details = []
        for pos in positions["data"]:
            total = float(pos.get("total", "0"))
            available = float(pos.get("available", "0"))
            locked = float(pos.get("locked", "0"))            
            if total > 0 or available > 0 or locked > 0:
                position_details.append({
                    "symbol": pos.get("symbol"),
                    "holdSide": pos.get("holdSide"),
                    "total": pos.get("total"),
                    "available": pos.get("available"), 
                    "locked": pos.get("locked"),
                    "marginMode": pos.get("marginMode"),
                    "marginCoin": pos.get("marginCoin"),
                    "leverage": pos.get("leverage"),
                    "unrealizedPL": pos.get("unrealizedPL"),
                    "markPrice": pos.get("markPrice")
                })        
        return json.dumps({
            "total_positions": len(position_details),
            "position_details": position_details
        }, ensure_ascii=False, indent=2)        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
    
@mcp.tool()
async def get_bitget_leverage_info(symbol: str = None) -> str:
    """
    Get leverage information for specific symbol or all symbols.
    
    Args:
        symbol: Trading symbol (optional, e.g., BTCUSDT)
    """
    try:
        client = get_bitget_client()
        
        # 계약 정보에서 레버리지 정보 조회
        exchange_info = client.get_exchange_info(symbol=symbol)
        
        if exchange_info.get("code") != "00000":
            return json.dumps({"error": "Failed to get exchange info", "response": exchange_info}, ensure_ascii=False, indent=2)
        
        leverage_info = []
        
        for contract in exchange_info.get("data", []):
            symbol_name = contract.get("symbol", "")
            max_leverage = contract.get("maxLever", "1")
            min_leverage = contract.get("minLever", "1")  # 보통 1배
            
            # 현재 포지션에서 실제 사용 중인 레버리지 확인
            positions = client.get_all_positions()
            current_leverage = "No position"
            
            if positions.get("code") == "00000":
                for pos in positions.get("data", []):
                    if pos.get("symbol") == symbol_name:
                        total = float(pos.get("total", "0"))
                        if total > 0:  # 포지션이 있으면
                            current_leverage = pos.get("leverage", "Unknown")
                            break
            
            leverage_info.append({
                "symbol": symbol_name,
                "current_leverage": current_leverage,
                "max_leverage": max_leverage,
                "min_leverage": min_leverage,
                "status": contract.get("symbolStatus", "unknown")
            })
        
        return json.dumps({
            "leverage_info": leverage_info,
            "total_symbols": len(leverage_info)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)    

if __name__ == "__main__":
    server_host = os.getenv("MCP_SERVER_HOST", "localhost")
    server_port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host=server_host,
        port=server_port                     
    )